from flask import Flask, request, jsonify
import boto3
import json
import uuid

app = Flask(__name__)
sns = boto3.client('sns', region_name='us-east-1')
TOPIC_ARN = 'SEU_TOPIC_ARN'
@app.route('/pedido', methods=['POST'])
def criar_pedido():
    data = request.json
    pedido = {
        "pedidoId": str(uuid.uuid4()),
        "valor": data.get("valor")
    }
    print(f"Pedido recevido: {pedido['pedidoId']} - Valor: {pedido['valor']}")
    sns.publish(
        TopicArn=TOPIC_ARN,
        Message=json.dumps(pedido))
    print("→ Pedido enviado para SNS")
    return jsonify(pedido)
app.run(host='0.0.0.0', port=80, debug=True)