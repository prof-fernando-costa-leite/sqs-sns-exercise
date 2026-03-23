from flask import Flask, request, jsonify
import boto3
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import uuid
import sys

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

app = Flask(__name__)

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL') or None
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
PORT = int(os.getenv('PORT', '8080'))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'

sns = boto3.client('sns', region_name=AWS_REGION, endpoint_url=AWS_ENDPOINT_URL)


def validate_configuration():
    """Valida configuração antes de iniciar o producer."""
    errors = []

    if not SNS_TOPIC_ARN:
        errors.append('❌ SNS_TOPIC_ARN não está configurada no .env')
    elif 'arn:aws:sns' not in SNS_TOPIC_ARN.lower():
        errors.append(f'❌ SNS_TOPIC_ARN parece inválida: {SNS_TOPIC_ARN}')

    if not AWS_REGION:
        errors.append('❌ AWS_REGION não está configurada')

    if errors:
        print('\n'.join(errors))
        print('\n💡 Verifique se o arquivo .env foi preenchido corretamente.')
        return False

    print(f'✅ Configuração validada:')
    print(f'   AWS_REGION: {AWS_REGION}')
    print(f'   SNS_TOPIC_ARN: {SNS_TOPIC_ARN}')
    if AWS_ENDPOINT_URL:
        print(f'   AWS_ENDPOINT_URL: {AWS_ENDPOINT_URL} (LocalStack)')
    else:
        print(f'   Usando IAM Role da EC2')
    print(f'   PORT: {PORT}')
    return True


def check_aws_credentials():
    """Verifica se boto3 consegue detectar credenciais."""
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials:
            print(f'✅ Credenciais detectadas: {credentials.access_key[:10]}...')
            return True
        else:
            print('⚠️  Nenhuma credencial encontrada localmente.')
            print('   Se estiver em EC2, verifique se a IAM Role está anexada.')
            return False
    except Exception as e:
        print(f'❌ Erro ao verificar credenciais: {e}')
        return False


@app.route('/pedido', methods=['POST'])
def criar_pedido():
    if not SNS_TOPIC_ARN:
        return jsonify({'erro': 'Defina a variável de ambiente SNS_TOPIC_ARN'}), 500

    data = request.get_json(silent=True) or {}
    valor = data.get('valor')
    if valor is None:
        return jsonify({'erro': 'O campo "valor" é obrigatório'}), 400

    pedido = {
        'pedidoId': str(uuid.uuid4()),
        'valor': valor,
    }
    print(f"Pedido recebido: {pedido['pedidoId']} - Valor: {pedido['valor']}")
    sns.publish(TopicArn=SNS_TOPIC_ARN, Message=json.dumps(pedido))
    print('→ Pedido enviado para SNS')
    return jsonify(pedido), 201


if __name__ == '__main__':
    print('=' * 60)
    print('PRODUCER - SNS/SQS')
    print('=' * 60 + '\n')

    if not validate_configuration():
        sys.exit(1)
    print()
    if not check_aws_credentials():
        sys.exit(1)
    print()
    print(f'🚀 Iniciando servidor na porta {PORT}...')
    print(f'   POST http://localhost:{PORT}/pedido\n')

    app.run(host='0.0.0.0', port=PORT, debug=FLASK_DEBUG)
