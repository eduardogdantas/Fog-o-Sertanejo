import sqlite3

import sqlite3

def iniciar_banco():
    conexao = sqlite3.connect('restaurante.db')
    cursor = conexao.cursor()

    # 1. Cria a tabela de mesas
    cursor.execute('''CREATE TABLE IF NOT EXISTS mesas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            numero INTEGER, 
                            status TEXT, 
                            praca_id INTEGER)''')
    
    # 2. Verifica se a tabela está vazia. Se estiver, cria as 40 mesas
    cursor.execute('SELECT COUNT(*) FROM mesas')
    if cursor.fetchone()[0] == 0:
        for i in range(1, 41):
            praca = ((i - 1) // 10) + 1 
            cursor.execute('INSERT INTO mesas (numero, status, praca_id) VALUES (?, ?, ?)', (i, 'Disponivel', praca))
        print("40 mesas criadas com sucesso!")

    # 3. Garante a tabela pedidos com a coluna preco
    cursor.execute('DROP TABLE IF EXISTS pedidos')
    cursor.execute('''CREATE TABLE pedidos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            mesa_numero INTEGER NOT NULL,
                            produto TEXT NOT NULL,
                            quantidade INTEGER NOT NULL,
                            preco REAL DEFAULT 0)''')
    
    # 4. Cria as outras tabelas necessárias
    cursor.execute('CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY, nome TEXT, quantidade INTEGER, preco REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS caixa (id INTEGER PRIMARY KEY, status TEXT, valor_inicial REAL, valor_final REAL, data TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')

    # 5. Adiciona a tabela de finanças
    cursor.execute('''CREATE TABLE IF NOT EXISTS financas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        descricao TEXT NOT NULL,
                        valor REAL NOT NULL,
                        tipo TEXT NOT NULL,
                        data TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conexao.commit()
    conexao.close()
    print("Banco de dados configurado e tabelas atualizadas!")

    
def criar_tabela_estoque():
    conexao = sqlite3.connect('restaurante.db')
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            preco REAL NOT NULL
        )
    ''')
    conexao.commit()
    conexao.close()

if __name__ == "__main__":
    iniciar_banco()