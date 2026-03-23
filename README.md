# Assyncronous

Exemplo simples de processamento assíncrono em Python usando SNS e SQS, preparado para rodar tanto localmente com LocalStack quanto na AWS.

## Visão geral

O projeto demonstra um fluxo básico de pedidos:

1. O produtor recebe um pedido via HTTP.
2. O produtor publica o pedido em um tópico SNS.
3. A fila SQS recebe a mensagem.
4. O consumidor lê a fila e processa o pedido.

## Importante: produtor e consumidor rodam separados

Sim: `producer` e `consumer` são processos diferentes.

Isso vale nos dois cenários:

- **localmente**, você roda `python producer/producer.py` em um terminal e `python consumer/consumer.py` em outro terminal
- **na AWS**, eles também continuam sendo componentes separados; por exemplo, você pode rodar o produtor em uma API/EC2/container e o consumidor em outro processo, outra VM, outro container ou outro serviço

O SNS e o SQS fazem a mediação assíncrona entre esses dois processos.

## Estrutura do projeto

```text
assyncronous/
├── .env.example
├── docker-compose.yml
├── README.md
├── requirements.txt
├── scripts/
│   └── bootstrap_localstack.sh
├── main.py
├── producer/
│   └── producer.py
└── consumer/
    └── consumer.py
```

## Arquivos principais

- `producer/producer.py`: sobe a API Flask em `POST /pedido` e publica no SNS
- `consumer/consumer.py`: fica escutando a fila SQS e processa os pedidos
- `scripts/bootstrap_localstack.sh`: cria automaticamente tópico, fila e assinatura no LocalStack
- `docker-compose.yml`: sobe o LocalStack com SNS e SQS
- `.env.example`: exemplo das variáveis de ambiente
- `requirements.txt`: dependências do projeto

## Pré-requisitos

### Para qualquer ambiente

- Python 3.10+
- ambiente virtual Python recomendado

### Para LocalStack

- Docker
- Docker Compose plugin (`docker compose`)
- AWS CLI instalada localmente

### Para AWS real

- credenciais AWS válidas
- um tópico SNS existente
- uma fila SQS existente
- assinatura da fila no tópico SNS

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Variáveis de ambiente

O projeto carrega o arquivo `.env` automaticamente no `producer` e no `consumer`.

### Variáveis suportadas

- `AWS_REGION`: região AWS. Padrão `us-east-1`
- `AWS_DEFAULT_REGION`: região padrão para AWS CLI e SDK
- `AWS_ENDPOINT_URL`: endpoint customizado. Use `http://localhost:4566` no LocalStack. Na AWS real, deixe vazio
- `AWS_ACCESS_KEY_ID`: credencial AWS ou valor fake no LocalStack
- `AWS_SECRET_ACCESS_KEY`: credencial AWS ou valor fake no LocalStack
- `SNS_TOPIC_NAME`: nome do tópico usado no bootstrap local
- `SQS_QUEUE_NAME`: nome da fila usada no bootstrap local
- `SNS_TOPIC_ARN`: ARN do tópico SNS usado pelo produtor
- `SQS_QUEUE_URL`: URL da fila SQS usada pelo consumidor
- `PORT`: porta HTTP do produtor. Padrão `8080`
- `FLASK_DEBUG`: `true` ou `false`
- `WAIT_TIME_SECONDS`: tempo de long polling do consumidor

## Rodando localmente com LocalStack

Esse é o fluxo mais simples agora.

### 1. Suba o LocalStack

```bash
docker compose up -d
```

### 2. Execute o bootstrap automático

Esse script:

- cria o tópico SNS
- cria a fila SQS
- cria a assinatura SNS -> SQS
- atualiza o arquivo `.env` com `SNS_TOPIC_ARN` e `SQS_QUEUE_URL`

```bash
chmod +x scripts/bootstrap_localstack.sh
./scripts/bootstrap_localstack.sh
```

### 3. Rode o consumidor

Em um terminal separado:

```bash
source .venv/bin/activate
python consumer/consumer.py
```

### 4. Rode o produtor

Em outro terminal separado:

```bash
source .venv/bin/activate
python producer/producer.py
```

### 5. Envie um pedido de teste

```bash
curl -X POST http://localhost:8080/pedido \
  -H 'Content-Type: application/json' \
  -d '{"valor": 150.0}'
```

### 6. Resultado esperado

No terminal do produtor:

- recebimento do pedido
- publicação no SNS

No terminal do consumidor:

- leitura da mensagem da fila
- processamento do pedido
- simulação de nota fiscal e email

## Rodando na AWS

Na AWS, o comportamento lógico é o mesmo: o produtor e o consumidor continuam separados.

### Cenário típico

- **produtor**: roda em um processo responsável por receber chamadas HTTP
- **consumidor**: roda em outro processo responsável por consumir a fila
- **SNS/SQS**: conectam esses dois lados de forma assíncrona

### 1. Prepare os recursos AWS

Você precisa ter:

- um tópico SNS
- uma fila SQS
- a fila assinada no tópico SNS
- permissões IAM adequadas para publicar no SNS e consumir/apagar mensagens da SQS

### 2. Configure o `.env` para AWS

Exemplo:

```bash
cat > .env <<'EOF'
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1
PORT=8080
FLASK_DEBUG=false
WAIT_TIME_SECONDS=10
SNS_TOPIC_NAME=pedidos
SQS_QUEUE_NAME=pedidos-queue
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:pedidos
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/pedidos-queue
EOF
```

Observações:

- na AWS real, normalmente **não** configure `AWS_ENDPOINT_URL`
- `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY` podem vir do ambiente, perfil, role IAM ou credenciais já configuradas na máquina/instância/container

### 3. Rode o consumidor

Em um processo/terminal:

```bash
source .venv/bin/activate
python consumer/consumer.py
```

### 4. Rode o produtor

Em outro processo/terminal:

```bash
source .venv/bin/activate
python producer/producer.py
```

### 5. Envie um pedido de teste

```bash
curl -X POST http://localhost:8080/pedido \
  -H 'Content-Type: application/json' \
  -d '{"valor": 150.0}'
```

> Se o produtor estiver publicado em outra máquina, container ou serviço na AWS, ajuste a URL do `curl` para o endereço real dessa aplicação.

## Contrato atual do sistema

### Entrada do produtor

`POST /pedido`

Payload esperado:

```json
{
  "valor": 150.0
}
```

### Saída do produtor

Resposta de sucesso:

```json
{
  "pedidoId": "<uuid>",
  "valor": 150.0
}
```

### Erros tratados

- `500` se `SNS_TOPIC_ARN` não estiver configurada
- `400` se o campo `valor` não for enviado

## Comportamento atual do código

### `producer/producer.py`

- carrega `.env` automaticamente
- lê `AWS_REGION`, `AWS_ENDPOINT_URL`, `SNS_TOPIC_ARN`, `PORT` e `FLASK_DEBUG`
- valida configuração e payload
- publica a mensagem no SNS

### `consumer/consumer.py`

- carrega `.env` automaticamente
- lê `AWS_REGION`, `AWS_ENDPOINT_URL`, `SQS_QUEUE_URL` e `WAIT_TIME_SECONDS`
- faz long polling na fila
- processa mensagens em loop contínuo
- evita duplicados apenas em memória

## Limitações atuais

- `main.py` ainda está com o conteúdo padrão da IDE
- a deduplicação do consumidor é apenas em memória
- o consumidor assume o formato de mensagem SNS entregue via SQS
- o bootstrap local depende de `aws` CLI instalada

## Próximos passos sugeridos

- adicionar testes automatizados
- criar um `Makefile` para concentrar os comandos mais usados
- adicionar `healthcheck` e espera ativa para o LocalStack
- empacotar produtor e consumidor em containers separados
