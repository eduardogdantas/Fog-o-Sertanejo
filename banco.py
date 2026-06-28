import sqlite3
from datetime import datetime

def conectar():
    # Conecta ao arquivo de banco de dados do restaurante
    return sqlite3.connect("restaurante.db")

def inicializar_banco():
    conn = conectar()
    cursor = conn.cursor()
    # Estrutura das tabelas
    tabelas = [
        "CREATE TABLE IF NOT EXISTS mesas (numero INTEGER PRIMARY KEY, status TEXT DEFAULT 'Disponível', valor REAL DEFAULT 0.0)",
        "CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE NOT NULL, preco REAL NOT NULL, quantidade INTEGER NOT NULL)",
        "CREATE TABLE IF NOT EXISTS vendas_dia (id INTEGER PRIMARY KEY AUTOINCREMENT, mesa TEXT NOT NULL, valor REAL NOT NULL, horario TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS fluxo_caixa (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT NOT NULL, valor REAL NOT NULL, descricao TEXT, horario TEXT)"
    ]
    for sql in tabelas: 
        cursor.execute(sql)
    
    # Garante que as 40 mesas existam ao iniciar o sistema
    cursor.execute("SELECT COUNT(*) FROM mesas")
    if cursor.fetchone()[0] == 0:
        for i in range(1, 41):
            cursor.execute("INSERT INTO mesas (numero, status, valor) VALUES (?, 'Disponível', 0.0)", (i,))
    
    conn.commit()
    conn.close()

# --- MÓDULO DE MESAS ---
def obter_todas_mesas():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT numero, status FROM mesas ORDER BY numero ASC")
    dados = cursor.fetchall()
    conn.close()
    return dados

# --- MÓDULO DE PRODUTOS ---
def adicionar_produto(nome, preco, qtd):
    conn = conectar()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO produtos (nome, preco, quantidade) VALUES (?, ?, ?)", (nome, preco, qtd))
        conn.commit()
    except sqlite3.IntegrityError:
        # Retorna erro caso o produto já exista (evita que o programa feche)
        raise ValueError("Produto duplicado")
    finally:
        conn.close()

def remover_produto(id_p):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = ?", (id_p,))
    conn.commit()
    conn.close()

def alterar_produto(id_p, nome, preco, qtd):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("UPDATE produtos SET nome = ?, preco = ?, quantidade = ? WHERE id = ?", (nome, preco, qtd, id_p))
    conn.commit()
    conn.close()

def obter_produtos():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM produtos")
    dados = cursor.fetchall()
    conn.close()
    return dados

# --- MÓDULO DE CAIXA E VENDAS ---
def obter_vendas_do_dia():
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT mesa, valor, horario FROM vendas_dia WHERE horario LIKE ?", (f"{data_hoje}%",))
    dados = cursor.fetchall()
    conn.close()
    return dados

def obter_fluxo_caixa_dia():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT tipo, valor, descricao, horario FROM fluxo_caixa")
    dados = cursor.fetchall()
    conn.close()
    return dados
def obter_info_mesa(numero):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT status, valor FROM mesas WHERE numero = ?", (numero,))
    dados = cursor.fetchone()
    conn.close()
    return dados