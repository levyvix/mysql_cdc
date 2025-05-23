import json
import os
import time
from datetime import datetime
from typing import Any, Literal, Optional

import pymysql
from cyclopts import App
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    RowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent,
)
from rich import print_json

# Global variables

app = App(
    name="mysql-cdc-to-pubsub",
    version="0.1.0",
)

ENVIRONMENT = None
publisher = None
topic_path = None
pubsub_v1 = None


def set_environment(env: Optional[Literal["dev", "prod"]] = None) -> None:
    """Set the global environment configuration"""

    global ENVIRONMENT, pubsub_v1

    ENVIRONMENT = env or os.environ.get("ENVIRONMENT", "dev").lower()

    # Import Pub/Sub only in prod mode
    if ENVIRONMENT == "prod":
        try:
            from google.cloud import pubsub_v1

            globals()["pubsub_v1"] = pubsub_v1
        except ImportError:
            print(
                "Warning: google-cloud-pubsub package not found. Please install it for production mode."
            )
            raise


# Configurações
CONFIG = {
    "dev": {
        "mysql": {
            "host": "localhost",
            "user": "testuser",
            "password": "testpass",
            "database": "testdb",
        }
    },
    "prod": {
        "mysql": {
            "host": "localhost",
            "user": "testuser",
            "password": "testpass",
            "database": "testdb",
        },
        "gcp": {"project_id": "galvanic-flame-384620", "topic_id": "mysql-topic"},
    },
}


def init_pubsub_client():
    """Initialize Pub/Sub client (only in prod mode)"""
    global pubsub_v1

    if ENVIRONMENT == "prod" and pubsub_v1:
        try:
            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(
                CONFIG["prod"]["gcp"]["project_id"], CONFIG["prod"]["gcp"]["topic_id"]
            )
            return publisher, topic_path
        except Exception as e:
            print(f"Error initializing Pub/Sub client: {e}")
            raise
    return None, None


# Inicializa cliente Pub/Sub se estivermos em produção
publisher, topic_path = init_pubsub_client()


def get_mysql_config() -> dict[str, str]:
    """Return MySQL configuration based on environment"""
    if ENVIRONMENT is None:
        raise RuntimeError("Environment not initialized")
    return CONFIG[ENVIRONMENT]["mysql"]


def get_latest_binlog_position():
    """Recupera a última posição processada ou inicia do começo"""
    try:
        with open("binlog_position.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"log_file": "", "log_pos": 0}


def setup_binlog_connection() -> BinLogStreamReader:
    """Configura conexão MySQL com CDC habilitado"""
    mysql_config = get_mysql_config()
    conn = pymysql.connect(
        host=mysql_config["host"],
        user=mysql_config["user"],
        password=mysql_config["password"],
        database=mysql_config["database"],
    )
    cursor = conn.cursor()

    # Verifica se o binlog está habilitado
    cursor.execute("SHOW VARIABLES LIKE 'log_bin'")
    log_bin = cursor.fetchone()

    if log_bin and log_bin[1].lower() != "on":
        raise Exception("Binary logging not enabled on MySQL server")

    # Obtém posição atual do binlog
    cursor.execute("SHOW MASTER STATUS")
    binlog_info = cursor.fetchone()
    if binlog_info is None:
        raise Exception("Não foi possível obter a posição atual do binlog")

    current_log_file = binlog_info[0]
    current_log_pos = binlog_info[1]

    # Cria conexão para streaming de binlog
    stream = BinLogStreamReader(
        connection_settings=mysql_config,
        server_id=100,
        blocking=True,
        only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent],
        log_file=current_log_file,
        log_pos=current_log_pos,
        resume_stream=True,
    )

    return stream


def row_to_dict(row: dict[str, Any]) -> dict[str, Any]:
    """Converte row para dict serializável"""
    result: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, bytes):
            result[key] = value.decode("utf-8", errors="replace")
        else:
            result[key] = value
    return result


def process_binlog_event(event: RowsEvent) -> None:
    """Processa um evento de binlog e publica

    Args:
        event (RowsEvent): Evento de binlog.
    """

    db_name = event.schema
    table_name = event.table

    # Preparar dados baseado no tipo de evento
    if isinstance(event, WriteRowsEvent):
        operation = "INSERT"
        if event.rows:
            for row in event.rows:
                data = {
                    "operation": operation,
                    "database": db_name,
                    "table": table_name,
                    "primary_key": event.primary_key,
                    "data": row_to_dict(row["values"]),
                    "timestamp": datetime.now().isoformat(),
                }
                publish_data(json.dumps(data, indent=2))

    elif isinstance(event, UpdateRowsEvent):
        operation = "UPDATE"
        if event.rows:
            for row in event.rows:
                data = {
                    "operation": operation,
                    "database": db_name,
                    "table": table_name,
                    "primary_key": event.primary_key,
                    "data_before": row_to_dict(row["before_values"]),
                    "data_after": row_to_dict(row["after_values"]),
                    "timestamp": datetime.now().isoformat(),
                }
                publish_data(json.dumps(data, indent=2))

    elif isinstance(event, DeleteRowsEvent):
        operation = "DELETE"
        if event.rows:
            for row in event.rows:
                data = {
                    "operation": operation,
                    "database": db_name,
                    "table": table_name,
                    "primary_key": event.primary_key,
                    "data": row_to_dict(row["values"]),
                    "timestamp": datetime.now().isoformat(),
                }
                publish_data(json.dumps(data, indent=2))


def publish_data(data: str):
    """
    Publica dados no Pub/Sub (prod) ou terminal (dev)

    data: str - JSON serializável
    """

    data_dict = json.loads(data)

    if ENVIRONMENT == "prod":
        # Modo produção: publica no Pub/Sub
        if not publisher or not topic_path:
            raise RuntimeError("Pub/Sub client not initialized")
        try:
            message_bytes = data.encode("utf-8")
            future = publisher.publish(topic_path, data=message_bytes)
            message_id = future.result()
            print(
                f"Publicada mensagem {message_id}: {data_dict['operation']} em {data_dict['table']}"
            )
        except Exception as e:
            print(f"Erro ao publicar no Pub/Sub: {e}")
    else:
        # Modo dev: imprime no terminal
        operation_colors = {
            "INSERT": "\033[92m",  # Verde
            "UPDATE": "\033[93m",  # Amarelo
            "DELETE": "\033[91m",  # Vermelho
        }
        reset_color = "\033[0m"

        operation = data_dict["operation"]
        color = operation_colors.get(operation, "")

        print(f"\n{color}[{operation} em {data_dict['table']}]{reset_color}")
        print_json(data)
        print("-" * 50)


@app.default
def main(env: Optional[Literal["dev", "prod"]] = None):
    # Set environment based on command line argument
    set_environment(env)

    if ENVIRONMENT is None:
        raise RuntimeError("Failed to initialize environment")

    print(f"Iniciando CDC do MySQL em modo {ENVIRONMENT.upper()}...")
    if ENVIRONMENT == "dev":
        print("Alterações serão exibidas no terminal")
    else:
        print("Alterações serão publicadas no Pub/Sub")

    # Reinicializa cliente Pub/Sub se mudamos para prod
    if ENVIRONMENT == "prod":
        global publisher, topic_path
        publisher, topic_path = init_pubsub_client()

    while True:
        try:
            # Configura conexão com binlog
            stream = setup_binlog_connection()

            # Processa eventos continuamente
            for event in stream:
                process_binlog_event(event)

        except Exception as e:
            print(f"Erro no processamento CDC: {e}")
            print("Tentando reconectar em 10 segundos...")
            time.sleep(10)
        finally:
            if "stream" in locals() and stream:
                stream.close()


if __name__ == "__main__":
    app()
