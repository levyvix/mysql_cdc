# MySQL CDC (Change Data Capture)

Este projeto demonstra a implementação de Change Data Capture (CDC) com MySQL, capturando alterações no banco de dados em tempo real através do binlog.

## Pré-requisitos

- Docker e Docker Compose
- Python 3.8+
- UV (gerenciador de pacotes Python)

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/levyvix/mysql_cdc.git
cd mysql_cdc
```

2. Instale UV:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Instale as dependências usando UV:
```bash
uv sync
```

## Configuração do Ambiente

1. Inicie o container MySQL usando Docker Compose:
```bash
docker-compose up -d
```

2. Verifique se o container está rodando:
```bash
docker ps
```

## Carregando Dados de Teste

1. Execute o script de carga que vai criar a tabela e inserir dados iniciais:
```bash
uv run mysql-loader/load.py
```

Este script vai:
- Criar uma tabela `users`
- Inserir alguns registros iniciais
- Oferecer um menu interativo para simular alterações

## Executando o CDC

1. Em outro terminal, execute o script principal do CDC:
```bash
uv run main.py --env dev
```

O script vai:
- Conectar ao MySQL
- Monitorar alterações em tempo real
- Exibir as alterações no terminal com cores diferentes para cada operação:
  - 🟢 INSERT (verde)
  - 🟡 UPDATE (amarelo)
  - 🔴 DELETE (vermelho)

## Testando

1. Com o CDC rodando, volte ao terminal do loader e escolha 's' para simular alterações
2. Observe no terminal do CDC as alterações sendo capturadas em tempo real
3. O loader vai:
   - Inserir um novo usuário
   - Atualizar um usuário existente
   - Deletar o último usuário

## Estrutura do Projeto

mysql_cdc/
├── docker-compose.yaml # Configuração do container MySQL
├── mysql-config/
│ └── my.cnf # Configurações do MySQL (binlog)
├── mysql-loader/
│ └── load.py # Script para carregar dados de teste
└── main.py # Script principal do CDC



## Configurações do MySQL

O arquivo `my.cnf` já está configurado com as configurações necessárias para o CDC:
- Binary logging habilitado
- Formato ROW para o binlog
- Server ID configurado

## Troubleshooting

Se encontrar erros de permissão, certifique-se que o usuário `testuser` tem as permissões necessárias:

```sql
GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO 'testuser'@'%';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE ON testdb.* TO 'testuser'@'%';
FLUSH PRIVILEGES;
```

## Encerrando

Para encerrar tudo:

1. Pare o script CDC com Ctrl+C
2. Pare o container MySQL:
```bash
docker-compose down
```