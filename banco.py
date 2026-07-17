import sqlite3

def iniciar_banco():
    # Conecta (ou cria se não existir) o arquivo do banco de dados
    conexao = sqlite3.connect('restaurante.db')
    cursor = conexao.cursor()

    # Cria a tabela de mesas (se ela não existir)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mesas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero INTEGER NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    # NOVA TABELA: Caderno de pedidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa_numero INTEGER NOT NULL,
            produto TEXT NOT NULL,
            quantidade INTEGER NOT NULL
        )
    ''')
    # Verifica se já existem mesas cadastradas. Se não, cria as mesas de 1 a 40.
    cursor.execute('SELECT COUNT(*) FROM mesas')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 41):
            cursor.execute('INSERT INTO mesas (numero, status) VALUES (?, ?)', (i, 'Disponivel'))

    # Salva e fecha
    conexao.commit()
    conexao.close()
    print("Banco de dados configurado com sucesso!")

if __name__ == "__main__":
    iniciar_banco()