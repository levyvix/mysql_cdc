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
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# Inserindo alguns dados iniciais
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


# Função para simular alterações no banco
def simulate_changes():
    # Inserir novo usuário
    cursor.execute(
        "INSERT INTO users (name, email) VALUES (%s, %s)",
        ("Novo Usuário", f"novo{int(time.time())}@example.com"),
    )
    connection.commit()
    print("Inserido novo usuário")

    # Atualizar usuário existente
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
