#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
EXAMPLE_ENV_FILE="${ROOT_DIR}/.env.example"

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${EXAMPLE_ENV_FILE}" "${ENV_FILE}"
fi

set -a
source "${ENV_FILE}"
set +a

AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-$AWS_REGION}"
AWS_ENDPOINT_URL="${AWS_ENDPOINT_URL:-http://localhost:4566}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
SNS_TOPIC_NAME="${SNS_TOPIC_NAME:-pedidos}"
SQS_QUEUE_NAME="${SQS_QUEUE_NAME:-pedidos-queue}"
PORT="${PORT:-8080}"
FLASK_DEBUG="${FLASK_DEBUG:-true}"
WAIT_TIME_SECONDS="${WAIT_TIME_SECONDS:-10}"

AWS_CMD=(aws --endpoint-url="${AWS_ENDPOINT_URL}")

if ! command -v aws >/dev/null 2>&1; then
  echo "Erro: aws CLI não encontrada. Instale a AWS CLI para usar o bootstrap." >&2
  exit 1
fi

echo "[1/5] Criando tópico SNS '${SNS_TOPIC_NAME}'..."
SNS_TOPIC_ARN="$(${AWS_CMD[@]} sns create-topic --name "${SNS_TOPIC_NAME}" --query 'TopicArn' --output text)"

echo "[2/5] Criando fila SQS '${SQS_QUEUE_NAME}'..."
${AWS_CMD[@]} sqs create-queue --queue-name "${SQS_QUEUE_NAME}" >/dev/null
SQS_QUEUE_URL="$(${AWS_CMD[@]} sqs get-queue-url --queue-name "${SQS_QUEUE_NAME}" --query 'QueueUrl' --output text)"

echo "[3/5] Obtendo ARN da fila..."
SQS_QUEUE_ARN="$(${AWS_CMD[@]} sqs get-queue-attributes --queue-url "${SQS_QUEUE_URL}" --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)"

QUEUE_POLICY=$(cat <<JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Allow-SNS-SendMessage",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${SQS_QUEUE_ARN}",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "${SNS_TOPIC_ARN}"
        }
      }
    }
  ]
}
JSON
)

echo "[4/5] Aplicando policy na fila e criando assinatura SNS -> SQS..."
${AWS_CMD[@]} sqs set-queue-attributes \
  --queue-url "${SQS_QUEUE_URL}" \
  --attributes Policy="${QUEUE_POLICY}" >/dev/null
${AWS_CMD[@]} sns subscribe \
  --topic-arn "${SNS_TOPIC_ARN}" \
  --protocol sqs \
  --notification-endpoint "${SQS_QUEUE_ARN}" >/dev/null

echo "[5/5] Atualizando ${ENV_FILE} com os recursos resolvidos..."
python3 - <<PY
from pathlib import Path

env_path = Path(${ENV_FILE@Q})
values = {
    'AWS_REGION': ${AWS_REGION@Q},
    'AWS_DEFAULT_REGION': ${AWS_DEFAULT_REGION@Q},
    'AWS_ENDPOINT_URL': ${AWS_ENDPOINT_URL@Q},
    'AWS_ACCESS_KEY_ID': ${AWS_ACCESS_KEY_ID@Q},
    'AWS_SECRET_ACCESS_KEY': ${AWS_SECRET_ACCESS_KEY@Q},
    'SNS_TOPIC_NAME': ${SNS_TOPIC_NAME@Q},
    'SQS_QUEUE_NAME': ${SQS_QUEUE_NAME@Q},
    'SNS_TOPIC_ARN': ${SNS_TOPIC_ARN@Q},
    'SQS_QUEUE_URL': ${SQS_QUEUE_URL@Q},
    'PORT': ${PORT@Q},
    'FLASK_DEBUG': ${FLASK_DEBUG@Q},
    'WAIT_TIME_SECONDS': ${WAIT_TIME_SECONDS@Q},
}

existing_lines = []
if env_path.exists():
    existing_lines = env_path.read_text().splitlines()

updated = []
seen = set()
for line in existing_lines:
    if '=' in line and not line.lstrip().startswith('#'):
        key = line.split('=', 1)[0]
        if key in values:
            updated.append(f'{key}={values[key]}')
            seen.add(key)
            continue
    updated.append(line)

for key, value in values.items():
    if key not in seen:
        updated.append(f'{key}={value}')

env_path.write_text('\n'.join(updated) + '\n')
PY

echo "Bootstrap concluído com sucesso."
echo "SNS_TOPIC_ARN=${SNS_TOPIC_ARN}"
echo "SQS_QUEUE_URL=${SQS_QUEUE_URL}"
echo
echo "Agora rode o consumidor e o produtor em processos separados."

