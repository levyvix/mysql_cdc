import time

import pymysql

# Configuração da conexão
connection = pymysql.connect(
    host="localhost", user="testuser", password="testpass", database="testdb"
)

cursor = connection.cursor()

# Criando tabela de teste
print("Criando tabela de usuários...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
""")

# Verificar se a tabela está vazia
cursor.execute("SELECT COUNT(*) FROM users")
result = cursor.fetchone()
count = result[0] if result is not None else 0

# Inserindo dados iniciais apenas se a tabela estiver vazia
if count == 0:
    print("Inserindo dados iniciais...")
    users = [
        ("João Silva", "joao@example.com"),
        ("Maria Santos", "maria@example.com"),
        ("Pedro Costa", "pedro@example.com"),
    ]

    for name, email in users:
        cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))

    connection.commit()
    print(f"Inseridos {len(users)} usuários iniciais.")
else:
    print("Tabela já contém dados, pulando inserção inicial.")


# Função para simular alterações no banco
def simulate_changes():
    # Inserir novo usuário
    print("Inserindo novo usuário")
    cursor.execute(
        "INSERT INTO users (name, email) VALUES (%s, %s)",
        ("Novo Usuário", f"novo{int(time.time())}@example.com"),
    )
    connection.commit()
    print("Inserido novo usuário")

    # Atualizar usuário existente
    print("Atualizando usuário ID 1")
    cursor.execute(
        "UPDATE users SET email = %s WHERE id = 1",
        (f"atualizado{int(time.time())}@example.com",),
    )
    connection.commit()
    print("Atualizado usuário ID 1")

    # Excluir último usuário
    cursor.execute("DELETE FROM users ORDER BY id DESC LIMIT 1")
    connection.commit()
    print("Excluído último usuário")

    # adicionar varios usuarios
    print("Inserindo 3 novos usuários")
    users_to_insert = [
        ("Novo Usuário 2", f"novo2{int(time.time())}@example.com"),
        ("Novo Usuário 3", f"novo3{int(time.time())}@example.com"),
        ("Novo Usuário 4", f"novo4{int(time.time())}@example.com"),
    ]
    flattened_values = [val for user in users_to_insert for val in user]
    cursor.execute(
        "INSERT INTO users (name, email) VALUES (%s, %s), (%s, %s), (%s, %s)",
        flattened_values,
    )
    connection.commit()
    print("Inseridos 3 novos usuários")

    # excluindo os novos usuarios
    print("Excluindo 3 novos usuários")
    cursor.execute(
        """
        with last_insert_id as (
            select id from users order by id desc limit 3
        )
        delete from users where id in (select id from last_insert_id)
        """
    )
    connection.commit()
    print("Excluídos 3 novos usuários")


print("\nDados de teste prontos! Execute o script CDC para monitorar as mudanças.")
print("Para simular mudanças, execute a função simulate_changes() neste script.")

if __name__ == "__main__":
    user_input = input("\nDeseja simular mudanças agora? (s/n): ")
    if user_input.lower() == "s":
        simulate_changes()

    print("\nPara fechar a conexão, pressione Ctrl+C")
    try:
        while True:
            user_input = input("\nSimular mais mudanças? (s/n): ")
            if user_input.lower() == "s":
                simulate_changes()
            elif user_input.lower() == "n":
                break
    except KeyboardInterrupt:
        pass
    finally:
        cursor.close()
        connection.close()
        print("Conexão fechada.")
