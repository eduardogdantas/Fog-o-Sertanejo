from datetime import datetime
from flask import Flask, redirect, render_template, request, url_for
import sqlite3

app = Flask(__name__)


def conectar_db():
  return sqlite3.connect("restaurante.db")


@app.route("/")
def home():
  conexao = sqlite3.connect("restaurante.db")
  cursor = conexao.cursor()

  # 1. Busca todas as mesas
  cursor.execute("SELECT numero, status, praca_id FROM mesas ORDER BY numero")
  mesas = cursor.fetchall()

  # 2. Cria o dicionário das praças
  por_praca = {}
  for mesa in mesas:
    praca = mesa[2]
    if praca not in por_praca:
      por_praca[praca] = []
    por_praca[praca].append(mesa)

  conexao.close()

  # DEBUG: Isso vai imprimir no seu terminal do VS Code
  print(f"DEBUG: Encontrei {len(mesas)} mesas no banco.")

  return render_template("index.html", mesas=mesas, por_praca=por_praca)


@app.route("/mesa/<int:numero_mesa>")
def ver_mesa(numero_mesa):
  conexao = conectar_db()
  cursor = conexao.cursor()

  # Busca a mesa
  cursor.execute(
      "SELECT numero, status FROM mesas WHERE numero = ?", (numero_mesa,)
  )
  mesa_atual = cursor.fetchone()

  # Busca os pedidos DESSA mesa específica
  cursor.execute(
      "SELECT produto, quantidade FROM pedidos WHERE mesa_numero = ?",
      (numero_mesa,),
  )
  pedidos_da_mesa = cursor.fetchall()

  conexao.close()

  # Envia a mesa e a lista de pedidos para o HTML
  return render_template("mesa.html", mesa=mesa_atual, pedidos=pedidos_da_mesa)


@app.route("/mudar_status/<int:numero_mesa>/<novo_status>")
def mudar_status(numero_mesa, novo_status):
  conexao = conectar_db()
  cursor = conexao.cursor()
  cursor.execute(
      "UPDATE mesas SET status = ? WHERE numero = ?", (novo_status, numero_mesa)
  )
  conexao.commit()
  conexao.close()
  return redirect(url_for("ver_mesa", numero_mesa=numero_mesa))


def atualizar_status_mesa(numero_mesa, novo_status):
  conexao = conectar_db()
  cursor = conexao.cursor()
  cursor.execute(
      "UPDATE mesas SET status = ? WHERE numero = ?", (novo_status, numero_mesa)
  )
  conexao.commit()
  conexao.close()


@app.route("/adicionar_pedido/<int:numero_mesa>", methods=["POST"])
def adicionar_pedido(numero_mesa):
  produto = request.form.get("produto")
  quantidade = int(request.form.get("quantidade", 1))

  if not produto:
    return "Erro: O campo produto não foi enviado!", 400

  conexao = conectar_db()
  cursor = conexao.cursor()

  # 1. BUSCA O PREÇO NO ESTOQUE ANTES DE SALVAR
  cursor.execute("SELECT preco FROM estoque WHERE nome = ?", (produto,))
  resultado = cursor.fetchone()
  preco_unitario = resultado[0] if resultado else 0.0

  # 2. SALVA O PEDIDO COM O PREÇO
  cursor.execute(
      "INSERT INTO pedidos (mesa_numero, produto, quantidade, preco) VALUES"
      " (?, ?, ?, ?)",
      (numero_mesa, produto, quantidade, preco_unitario),
  )
  conexao.commit()
  conexao.close()

  # 3. Atualiza o status para 'Ocupada'
  atualizar_status_mesa(numero_mesa, "Ocupada")

  return redirect(url_for("ver_mesa", numero_mesa=numero_mesa))


@app.route("/estoque", methods=["GET", "POST"])
def gerenciar_estoque():
  conexao = sqlite3.connect("restaurante.db")
  cursor = conexao.cursor()

  # Garante que a tabela exista antes de qualquer operação
  cursor.execute("""CREATE TABLE IF NOT EXISTS estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                nome TEXT NOT NULL, 
                quantidade INTEGER NOT NULL, 
                preco REAL NOT NULL)""")

  if request.method == "POST":
    acao = request.form.get("acao")
    nome = request.form.get("nome")
    qtd = int(request.form.get("quantidade") or 0)
    preco_input = request.form.get("preco", "0")
    preco = float(preco_input.replace(",", "."))

    try:
      if acao == "adicionar":
        cursor.execute(
            "INSERT INTO estoque (nome, quantidade, preco) VALUES (?, ?, ?)",
            (nome, qtd, preco),
        )
      elif acao == "remover":
        cursor.execute("DELETE FROM estoque WHERE nome = ?", (nome,))
      elif acao == "alterar":
        cursor.execute(
            "UPDATE estoque SET quantidade = ?, preco = ? WHERE nome = ?",
            (qtd, preco, nome),
        )
      conexao.commit()
    except Exception as e:
      print(f"Erro no banco: {e}")

  cursor.execute("SELECT * FROM estoque")
  itens = cursor.fetchall()
  conexao.close()
  return render_template("estoque.html", itens=itens)


@app.route("/caixa", methods=["GET", "POST"])
def gerenciar_caixa():
  conexao = sqlite3.connect("restaurante.db")
  cursor = conexao.cursor()

  cursor.execute("""CREATE TABLE IF NOT EXISTS caixa 
                    (id INTEGER PRIMARY KEY, status TEXT, valor_inicial REAL, valor_final REAL, data TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

  if request.method == "POST":
    acao = request.form.get("acao")

    if acao == "abrir":
      valor = float(request.form.get("valor", 0))
      cursor.execute(
          "INSERT INTO caixa (status, valor_inicial) VALUES ('aberto', ?)",
          (valor,),
      )
      conexao.commit()

    elif acao == "fechar":
      cursor.execute(
          "SELECT mesa_numero, produto, quantidade, preco FROM pedidos"
      )
      itens_vendidos = cursor.fetchall()

      total_vendas = 0
      data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

      for item in itens_vendidos:
        mesa, produto, qtd, preco = item
        subtotal = float(qtd) * float(preco)
        total_vendas += subtotal

        # REGISTRA CADA ITEM NO FINANCEIRO COM A DATA CORRETA
        cursor.execute(
            "INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (?,"
            " ?, ?, ?)",
            (f"Venda Mesa {mesa}: {produto} (x{qtd})", subtotal, "Receita", data_atual),
        )

      cursor.execute(
          "UPDATE caixa SET status = 'fechado', valor_final = ? WHERE status ="
          " 'aberto'",
          (total_vendas,),
      )
      cursor.execute("DELETE FROM pedidos")
      cursor.execute("UPDATE mesas SET status = 'Disponivel'")
      conexao.commit()

    return redirect("/caixa")

  cursor.execute("SELECT * FROM caixa ORDER BY id DESC")
  registros = cursor.fetchall()
  conexao.close()

  return render_template("caixa.html", registros=registros)


@app.route("/relatorio")
def relatorio_vendas():
  conexao = sqlite3.connect("restaurante.db")
  cursor = conexao.cursor()
  cursor.execute("SELECT nome_item, quantidade, preco_total FROM vendas")
  vendas = cursor.fetchall()
  cursor.execute("SELECT SUM(preco_total) FROM vendas")
  total_geral = cursor.fetchone()[0] or 0.0
  conexao.close()
  return render_template("relatorio.html", vendas=vendas, total=total_geral)


@app.route("/financeiro")
def financeiro():
  conexao = sqlite3.connect("restaurante.db")
  cursor = conexao.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            valor REAL,
            tipo TEXT,
            data TEXT
        )
    """)
  conexao.commit()

  # Busca todas as movimentações ordenadas da mais recente para a mais antiga
  cursor.execute("SELECT * FROM financeiro ORDER BY id DESC")
  movimentacoes = cursor.fetchall()

  # Calcula apenas o total vendido (Receitas)
  cursor.execute("SELECT SUM(valor) FROM financeiro WHERE tipo = 'Receita'")
  resultado = cursor.fetchone()[0]
  total_vendido = resultado if resultado else 0.0

  conexao.close()
  return render_template(
      "financeiro.html", movimentacoes=movimentacoes, total_vendido=total_vendido
  )


@app.route("/adicionar_financa", methods=["POST"])
def adicionar_financa():
  descricao = request.form.get("descricao")
  valor = float(request.form.get("valor", 0))
  tipo = request.form.get("tipo")
  data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  conexao = conectar_db()
  cursor = conexao.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            valor REAL,
            tipo TEXT,
            data TEXT
        )
    """)
  cursor.execute(
      "INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (?, ?, ?,"
      " ?)",
      (descricao, valor, tipo, data_atual),
  )
  conexao.commit()
  conexao.close()
  return redirect(url_for("financeiro"))


@app.route("/limpar_financas", methods=["POST"])
def limpar_financas():
  conexao = sqlite3.connect("restaurante.db")
  cursor = conexao.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            valor REAL,
            tipo TEXT,
            data TEXT
        )
    """)
  cursor.execute("DELETE FROM financeiro")
  conexao.commit()
  conexao.close()
  return redirect(url_for("financeiro"))


def registrar_venda_financeiro(mesa_numero):
  conexao = conectar_db()
  cursor = conexao.cursor()

  cursor.execute(
      "SELECT produto, quantidade, preco FROM pedidos WHERE mesa_numero = ?",
      (mesa_numero,),
  )
  itens = cursor.fetchall()
  data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

  for item in itens:
    produto, qtd, preco = item
    subtotal = float(qtd) * float(preco)
    print(
        f"DEBUG: Produto: {produto}, Qtd: {qtd}, Preço: {preco}, Subtotal:"
        f" {subtotal}"
    )

    # CORREÇÃO: Passando explicitamente a descrição, o valor real, o tipo e a data atual
    cursor.execute(
        "INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (?, ?, ?,"
        " ?)",
        (f"Venda Mesa {mesa_numero}: {produto} (x{qtd})", subtotal, "Receita", data_atual),
    )

  conexao.commit()
  conexao.close()


@app.route("/liberar_mesa/<int:numero_mesa>")
def liberar_mesa(numero_mesa):
  registrar_venda_financeiro(numero_mesa)

  conexao = conectar_db()
  cursor = conexao.cursor()
  cursor.execute("DELETE FROM pedidos WHERE mesa_numero = ?", (numero_mesa,))
  cursor.execute(
      "UPDATE mesas SET status = 'Disponivel' WHERE numero = ?", (numero_mesa,)
  )
  conexao.commit()
  conexao.close()

  return redirect(url_for("home"))


if __name__ == "__main__":
  app.run(debug=True)