from datetime import datetime
from flask import Flask, redirect, render_template, request, url_for, jsonify
import sqlite3
import re
from datetime import datetime
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
        # Se for adicionar, o campo 'nome' é texto. Se for alterar/remover, o select envia o ID.
        identificador = request.form.get("nome") 
        
        qtd_raw = request.form.get("quantidade", "0")
        try:
            qtd = float(qtd_raw)
        except ValueError:
            qtd = 0.0

        preco_input = request.form.get("preco", "0")
        try:
            preco = float(preco_input.replace(",", "."))
        except ValueError:
            preco = 0.0

        try:
            if acao == "adicionar":
                nome_prod = request.form.get("nome_texto", "")
                cursor.execute(
                    "INSERT INTO estoque (nome, quantidade, preco) VALUES (?, ?, ?)",
                    (nome_prod, int(qtd), preco),
                )
            elif acao == "remover":
                cursor.execute("DELETE FROM estoque WHERE id = ?", (identificador,))
            elif acao == "alterar":
                nome_prod = request.form.get("nome_texto", "")
                cursor.execute(
                    "UPDATE estoque SET nome = ?, quantidade = ?, preco = ? WHERE id = ?",
                    (nome_prod, int(qtd), preco, identificador),
                )
            elif acao == "reajustar":
                valor_reajuste = request.form.get("valor_reajuste", "0")
                try:
                    percentual = float(valor_reajuste.replace(",", ".")) / 100.0
                except ValueError:
                    percentual = 0.0
                
                cursor.execute("UPDATE estoque SET preco = preco + (preco * ?)", (percentual,))
                
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

@app.route('/api/gerar-relatorio', methods=['GET'])
def api_gerar_relatorio():
    tipo = request.args.get('tipo')
    data_inicio = request.args.get('inicio')
    data_fim = request.args.get('fim')
    
   
    resultados = []
    
    if tipo == 'vendas':
        # Exemplo de dados retornados para o relatório de vendas
        resultados = [
            {"id": 101, "descricao": "Venda de Produto A", "referencia": "Caixa 01", "valor": "R$ 150,00"},
            {"id": 102, "descricao": "Venda de Produto B", "referencia": "Caixa 01", "valor": "R$ 80,00"}
        ]
    elif tipo == 'financeiro':
        resultados = [
            {"id": 201, "descricao": "Pagamento de Fornecedor", "referencia": "Despesa", "valor": "R$ 300,00"}
        ]
        
    return jsonify(resultados)

@app.route('/relatorio')
def exibir_pagina_relatorio():
    return render_template('relatorios.html')

@app.route('/relatorios')
def relatorios():
    filtro_tipo = request.args.get('filtro', 'mes')
    
    # Pega o mês selecionado no input (Ex: "2026-07"). Se não escolher nada, pega o mês atual automaticamente.
    mes_atual_padrao = datetime.now().strftime('%Y-%m')
    mes_selecionado = request.args.get('mes_ano', mes_atual_padrao)
    
    conexao = sqlite3.connect("restaurante.db")
    cursor = conexao.cursor()
    
    # Faz a consulta considerando o filtro escolhido
    if filtro_tipo == 'tempo_real':
        cursor.execute("SELECT id, descricao, tipo, valor FROM financeiro WHERE tipo = 'Receita' ORDER BY id DESC")
    else:
        # Filtra pelo ano e mês correspondentes (assumindo que sua tabela salve a data ou ID sequencial. 
        # Como o SQLite armazena texto ou data, ajustamos para buscar pelo padrão do mês escolhido no formato AAAA-MM)
        # Nota: Se o seu banco salvar a data em outra coluna, ajuste o 'date(data)' ou o campo correspondente.
        query = "SELECT id, descricao, tipo, valor FROM financeiro WHERE tipo = 'Receita' AND strftime('%Y-%m', data) = ? ORDER BY id DESC"
        
        # Caso a sua tabela de financeiro ainda NÃO tenha uma coluna de data real e dê erro, 
        # use temporariamente a linha abaixo para não quebrar a página enquanto implementa a coluna de data:
        cursor.execute("SELECT id, descricao, tipo, valor FROM financeiro WHERE tipo = 'Receita' ORDER BY id DESC")
        
    dados = cursor.fetchall()
    conexao.close()
    
    resultados = []
    soma_total = 0.0
    contagem_pratos = {}
    
    for item in dados:
        id_item, desc, tipo, val = item
        soma_total += val

        if "Balcão" in desc:
            referencia_venda = "Balcão"
        elif "Mesa" in desc:
            referencia_venda = desc.split(':')[0].replace("Venda ", "")
        else:
            referencia_venda = "Outros"

        resultados.append({
            "id": id_item,
            "descricao": desc,
            "referencia": referencia_venda,
            "valor": f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        })
        
        match = re.search(r':\s*(.+?)\s*\(x(\d+)\)', desc)
        if match:
            nome_produto = match.group(1).strip().capitalize() 
            quantidade = int(match.group(2))
            contagem_pratos[nome_produto] = contagem_pratos.get(nome_produto, 0) + quantidade
            
    total_pedidos = len(resultados)

    if contagem_pratos:
        prato_destaque_nome = max(contagem_pratos, key=contagem_pratos.get)
        prato_destaque_qtd = contagem_pratos[prato_destaque_nome]
    else:
        prato_destaque_nome = "Sem vendas"
        prato_destaque_qtd = 0

    vendas_formatadas = f"R$ {soma_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return render_template(
        'relatorios.html',
        vendas_totais=vendas_formatadas,
        total_pessoas=total_pedidos,
        total_pedidos=total_pedidos,
        prato_destaque_nome=prato_destaque_nome,
        prato_destaque_qtd=prato_destaque_qtd,
        resultados=resultados,
        filtro_atual=filtro_tipo,
        mes_selecionado=mes_selecionado
    )
@app.route('/vendas')
def vendas():
    conexao = sqlite3.connect("restaurante.db")
    conexao.row_factory = sqlite3.Row
    cursor = conexao.cursor()
    cursor.execute("SELECT numero, status FROM mesas") 
    mesas = cursor.fetchall()

    por_praca = {} 
    for m in mesas:
        pass

    cursor.execute("SELECT * FROM estoque")
    estoque_itens = cursor.fetchall()
    
    conexao.close()
    
    return render_template(
        'vendas.html', 
        mesas=mesas, 
        por_praca=por_praca, 
        estoque_itens=estoque_itens
    )


@app.route("/cadastrar-usuario")
def cadastrar_usuario():
    return render_template("cadastrar_usuario.html") 

@app.route("/configuracao")
def configuracao():
    return render_template("configuracao.html")


@app.route("/logout")
def logout():
    return redirect(url_for("home"))
@app.route("/venda-balcao", methods=["POST"])
def venda_balcao():
    produto = request.form.get("produto")
    quantidade = int(request.form.get("quantidade", 1))
    pagamento = request.form.get("forma_pagamento", "Dinheiro")

    if not produto:
        return "Erro: O campo produto não foi enviado!", 400

    conexao = sqlite3.connect("restaurante.db")
    cursor = conexao.cursor()

    # Busca o preço no estoque
    cursor.execute("SELECT preco, quantidade FROM estoque WHERE nome = ?", (produto,))
    resultado = cursor.fetchone()
    
    if resultado:
        preco_unitario = resultado[0]
        estoque_atual = resultado[1]
        valor_total = preco_unitario * quantidade

        # Dá baixa no estoque
        novo_estoque = estoque_atual - quantidade
        cursor.execute("UPDATE estoque SET quantidade = ? WHERE nome = ?", (novo_estoque, produto))

        # Lança no financeiro
        descricao_venda = f"Venda Balcão: {produto} (x{quantidade}) - {pagamento}"
        cursor.execute(
            "INSERT INTO financeiro (descricao, tipo, valor) VALUES (?, 'Receita', ?)",
            (descricao_venda, valor_total)
        )
        conexao.commit()
        conexao.close()
        
        return redirect(url_for("vendas")) # Sucesso! Volta pra tela.
        
    else:
        # SE O PRODUTO NÃO EXISTIR NO ESTOQUE, ELE VAI MOSTRAR ESSA TELA DE ERRO:
        conexao.close()
        return f"<h1>ERRO!</h1> <p>O sistema tentou vender '<b>{produto}</b>', mas esse nome exato não existe na sua tabela de estoque.</p> <p>Volte e verifique o nome cadastrado.</p>"

if __name__ == "__main__":
    app.run(debug=True)