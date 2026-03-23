# Assyncronous

Exemplo simples de processamento assíncrono em Python usando AWS SNS e SQS.

## Visão geral

O projeto demonstra um fluxo básico de pedidos:

1. O produtor recebe um pedido via HTTP.
2. O pedido é publicado em um tópico SNS.
3. Uma fila SQS recebe a mensagem.
4. O consumidor lê a fila e processa o pedido.

## Estrutura do projeto

```text
assyncronous/
├── main.py
├── producer/
│   └── producer.py
└── consumer/
    └── consumer.py
```

### Arquivos principais

- `producer/producer.py`: sobe uma API Flask com a rota `POST /pedido` e publica mensagens no SNS.
- `consumer/consumer.py`: faz polling contínuo na fila SQS e simula o processamento do pedido.
- `main.py`: arquivo padrão do template da IDE, atualmente não faz parte do fluxo principal.

## Pré-requisitos

- Python 3.10+ (ou compatível com `Flask` e `boto3`)
- Credenciais AWS configuradas localmente
- Um tópico SNS criado na AWS
- Uma fila SQS assinada no tópico SNS

## Dependências

Pelo código atual, o projeto usa:

- `boto3`
- `Flask`

Se quiser instalar rapidamente em um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
pip install boto3 flask
```

## Configuração

Antes de executar, ajuste os placeholders no código:

### No produtor
Em `producer/producer.py`:

- substitua `SEU_TOPIC_ARN` pelo ARN real do tópico SNS

### No consumidor
Em `consumer/consumer.py`:

- substitua `SUA_QUEUE_URL` pela URL real da fila SQS

### Região AWS
Os dois scripts estão fixados em `us-east-1`:

- `boto3.client('sns', region_name='us-east-1')`
- `boto3.client('sqs', region_name='us-east-1')`

Se sua infraestrutura estiver em outra região, atualize esses valores.

## Como executar

### 1. Inicie o produtor

```bash
python producer/producer.py
```

Observação: o produtor está configurado para subir na porta `80` com `debug=True`. Em algumas máquinas Linux, a porta 80 pode exigir permissões elevadas. Se necessário, altere a porta no arquivo.

### 2. Inicie o consumidor

Em outro terminal:

```bash
python consumer/consumer.py
```

O consumidor ficará em loop contínuo aguardando mensagens.

## Exemplo de requisição

Com o produtor em execução, envie um pedido para a API:

```bash
curl -X POST http://localhost/pedido \
  -H 'Content-Type: application/json' \
  -d '{"valor": 150.0}'
```

Exemplo de resposta:

```json
{
  "pedidoId": "<uuid-gerado>",
  "valor": 150.0
}
```

## Fluxo esperado no terminal

### Produtor
- recebe o pedido
- gera um `pedidoId`
- publica no SNS

### Consumidor
- lê a mensagem da SQS
- evita reprocessamento básico em memória com `processed = set()`
- simula ações como:
  - gerar nota fiscal
  - enviar email

## Limitações atuais

- `main.py` ainda está com o conteúdo padrão da IDE.
- Não existe `requirements.txt` no projeto neste momento.
- A deduplicação do consumidor é apenas em memória; ao reiniciar o processo, os IDs processados são perdidos.
- O produtor assume que `request.json` contém a chave `valor`.
- O produtor está iniciando o servidor diretamente ao importar o arquivo.

## Próximos passos sugeridos

- adicionar um `requirements.txt`
- mover configurações para variáveis de ambiente
- trocar placeholders por leitura de `.env`
- melhorar validação de payload da rota `/pedido`
- proteger o `app.run(...)` com `if __name__ == '__main__':`

## Observação

Este repositório parece ser um exemplo didático de comunicação assíncrona entre serviços usando AWS. A documentação acima descreve o comportamento atual do código, sem assumir recursos que ainda não foram implementados.

