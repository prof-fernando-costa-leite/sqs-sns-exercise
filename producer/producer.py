from flask import Flask, request, jsonify
import boto3
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import uuid

load_dotenv(Path(__file__).resolve().parents[1] / '.env')

app = Flask(__name__)

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ENDPOINT_URL = os.getenv('AWS_ENDPOINT_URL') or None
SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
PORT = int(os.getenv('PORT', '8080'))
FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'

sns = boto3.client('sns', region_name=AWS_REGION, endpoint_url=AWS_ENDPOINT_URL)


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
    app.run(host='0.0.0.0', port=PORT, debug=FLASK_DEBUG)
