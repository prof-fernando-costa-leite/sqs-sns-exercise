import boto3
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import time
import sys

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL') or None
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
WAIT_TIME_SECONDS = int(os.getenv('WAIT_TIME_SECONDS', '10'))

processed = set()


def validate_configuration():
    """Valida configuração antes de iniciar o consumer."""
    errors = []

    if not SQS_QUEUE_URL:
        errors.append('❌ SQS_QUEUE_URL não está configurada no .env')
    elif 'sqs' not in SQS_QUEUE_URL.lower():
        errors.append(f'❌ SQS_QUEUE_URL parece inválida: {SQS_QUEUE_URL}')

    if not AWS_REGION:
        errors.append('❌ AWS_REGION não está configurada')

    if errors:
        print('\n'.join(errors))
        print('\n💡 Verifique se o arquivo .env foi preenchido corretamente.')
        sys.exit(1)

    print(f'✅ Configuração validada:')
    print(f'   AWS_REGION: {AWS_REGION}')
    print(f'   SQS_QUEUE_URL: {SQS_QUEUE_URL[:50]}...')
    if AWS_ENDPOINT_URL:
        print(f'   AWS_ENDPOINT_URL: {AWS_ENDPOINT_URL} (LocalStack)')
    else:
        print(f'   Usando IAM Role da EC2')


def check_aws_credentials():
    """Verifica se boto3 consegue detectar credenciais com retry."""
    max_retries = 5
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials:
                print(f'✅ Credenciais detectadas: {credentials.access_key[:10]}...')
                return True
        except Exception as e:
            pass

        if attempt < max_retries - 1:
            print(f'⏳ Tentando detectar credenciais... (tentativa {attempt + 1}/{max_retries})')
            time.sleep(retry_delay)

    print('⚠️  Nenhuma credencial encontrada após várias tentativas.')
    print('   Se estiver em EC2:')
    print('   1. Verifique se a IAM Role está anexada: ')
    print('      curl -s http://169.254.169.254/latest/meta-data/iam/security-credentials/')
    print('   2. Aguarde 30-60 segundos após iniciar a EC2 (metadata service leva tempo)')
    print('   3. Se ainda não funcionar, tente em outro terminal')
    return False


def create_sqs_client():
    return boto3.client('sqs', region_name=AWS_REGION, endpoint_url=AWS_ENDPOINT_URL)


def process_messages():
    if not SQS_QUEUE_URL:
        raise RuntimeError('Defina a variável de ambiente SQS_QUEUE_URL')

    sqs = create_sqs_client()

    print('🔄 Iniciando consumer...')
    print('   Aguardando mensagens da fila SQS...')
    print('   (Pressione Ctrl+C para parar)\n')

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=WAIT_TIME_SECONDS,
            )
            messages = response.get('Messages', [])
            if not messages:
                print(f'[{time.strftime("%H:%M:%S")}] Nenhuma mensagem disponível. Aguardando...')
                time.sleep(1)
                continue

            for message in messages:
                body = json.loads(message['Body'])
                pedido = json.loads(body.get('Message', '{}'))
                pedido_id = pedido.get('pedidoId')
                if not pedido_id:
                    print('Mensagem inválida ignorada: pedidoId ausente')
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=message['ReceiptHandle'],
                    )
                    continue
                if pedido_id in processed:
                    print('Duplicado ignorado')
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=message['ReceiptHandle'],
                    )
                    continue
                processed.add(pedido_id)
                print(f'✅ Processando pedido: {pedido_id}')
                print('→ Gerando nota fiscal...')
                print('→ Enviando email...')
                sqs.delete_message(
                    QueueUrl=SQS_QUEUE_URL,
                    ReceiptHandle=message['ReceiptHandle'],
                )
        except Exception as e:
            print(f'\n❌ Erro ao processar mensagens: {e}')
            print(f'   Tipo: {type(e).__name__}')
            print(f'   Verifique:')
            print(f'   1. IAM Role da EC2 tem permissão de SQS?')
            print(f'   2. SQS_QUEUE_URL está correta?')
            print(f'   3. A fila existe na região {AWS_REGION}?')
            time.sleep(5)


if __name__ == '__main__':
    print('=' * 60)
    print('CONSUMER - SNS/SQS')
    print('=' * 60 + '\n')

    validate_configuration()
    print()
    if not check_aws_credentials():
        sys.exit(1)
    print()
    process_messages()
