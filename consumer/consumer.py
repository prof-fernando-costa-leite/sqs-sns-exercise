import boto3
import json
sqs = boto3.client('sqs', region_name='us-east-1')
QUEUE_URL = 'SUA_QUEUE_URL'
processed = set()
while True:
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=10
    )
    messages = response.get('Messages', [])
    for message in messages:
        body = json.loads(message['Body'])
        pedido = json.loads(body['Message'])
        pedido_id = pedido['pedidoId']
        if pedido_id in processed:
            print('Duplicado ignorado')
            continue
        processed.add(pedido_id)
        print(f"Processando pedido: {pedido_id}")
        print("→ Gerando nota fiscal...")
        print("→ Enviando email...")
        sqs.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=message['ReceiptHandle']
        )