import boto3
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL') or None
SQS_QUEUE_URL = os.getenv('SQS_QUEUE_URL')
WAIT_TIME_SECONDS = int(os.getenv('WAIT_TIME_SECONDS', '10'))

processed = set()


def create_sqs_client():
    return boto3.client('sqs', region_name=AWS_REGION, endpoint_url=AWS_ENDPOINT_URL)


def process_messages():
    if not SQS_QUEUE_URL:
        raise RuntimeError('Defina a variável de ambiente SQS_QUEUE_URL')

    sqs = create_sqs_client()

    while True:
        response = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=WAIT_TIME_SECONDS,
        )
        messages = response.get('Messages', [])
        if not messages:
            print('Nenhuma mensagem disponível. Aguardando...')
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
            print(f'Processando pedido: {pedido_id}')
            print('→ Gerando nota fiscal...')
            print('→ Enviando email...')
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle'],
            )


if __name__ == '__main__':
    process_messages()
