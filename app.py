from datetime import datetime
from flask import Flask, redirect, render_template, request, url_for, jsonify
import sqlite3
import re

app = Flask(__name__)

def conectar_db():
  return sqlite3.connect("restaurante.db")

# ==========================================
# CRIAÇÃO AUTOMÁTICA DE TABELAS AO INICIAR
# ==========================================
def criar_tabelas():
    conexao = conectar_db()
    cursor = conexao.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_fechamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mesa_numero TEXT,
            produtos_json TEXT,
            total REAL,
            data_hora TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            senha TEXT
        )
    """)
    conexao.commit()
    conexao.close()

criar_tabelas()


@app.route("/")
def home():
    conexao = sqlite3.connect("restaurante.db")
    cursor = conexao.cursor()

    cursor.execute("SELECT numero, status, praca_id FROM mesas ORDER BY numero")
    mesas = cursor.fetchall()

    por_praca = {}
    for mesa in mesas:
        praca = mesa[2]
        if praca not in por_praca:
            por_praca[praca] = []
        por_praca[praca].append(mesa)

    cursor.execute("SELECT * FROM estoque")
    estoque_itens = cursor.fetchall()

    cursor.execute("SELECT id, mesa_numero, total, data_hora FROM historico_fechamentos ORDER BY id DESC LIMIT 20")
    vendas_db = cursor.fetchall()
    vendas_fechadas = [{'id': v[0], 'mesa': v[1], 'total': v[2], 'hora': v[3]} for v in vendas_db]

    conexao.close()

    return render_template("index.html", mesas=mesas, por_praca=por_praca, estoque_itens=estoque_itens, vendas_fechadas=vendas_fechadas)


@app.route("/mesa/<int:numero_mesa>")
def ver_mesa(numero_mesa):
    conexao = conectar_db()
    cursor = conexao.cursor()

    cursor.execute(
        "SELECT numero, status FROM mesas WHERE numero = ?", (numero_mesa,)
    )
    mesa_atual = cursor.fetchone()

    cursor.execute(
        "SELECT produto, quantidade FROM pedidos WHERE mesa_numero = ?",
        (numero_mesa,),
    )
    pedidos_da_mesa = cursor.fetchall()

    try:
        cursor.execute("SELECT nome, categoria FROM estoque WHERE quantidade > 0")
    except sqlite3.OperationalError:
        cursor.execute("SELECT nome, 'Cardápio Geral' as categoria FROM estoque WHERE quantidade > 0")
        
    produtos_brutos = cursor.fetchall()
    conexao.close()

    produtos_agrupados = {}
    for produto in produtos_brutos:
        nome_produto = produto[0]
        categoria = produto[1]
        
        if categoria not in produtos_agrupados:
            produtos_agrupados[categoria] = []
            
        produtos_agrupados[categoria].append({"nome": nome_produto})

    return render_template(
        'mesa.html', 
        mesa=mesa_atual, 
        pedidos=pedidos_da_mesa, 
        produtos_por_categoria=produtos_agrupados
    )


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

  cursor.execute("SELECT preco FROM estoque WHERE nome = ?", (produto,))
  resultado = cursor.fetchone()
  preco_unitario = resultado[0] if resultado else 0.0

  cursor.execute(
      "INSERT INTO pedidos (mesa_numero, produto, quantidade, preco) VALUES (?, ?, ?, ?)",
      (numero_mesa, produto, quantidade, preco_unitario),
  )
  conexao.commit()
  conexao.close()

  atualizar_status_mesa(numero_mesa, "Ocupada")

  return redirect(url_for("ver_mesa", numero_mesa=numero_mesa))


@app.route("/estoque", methods=["GET", "POST"])
def gerenciar_estoque():
    conexao = sqlite3.connect("restaurante.db")
    cursor = conexao.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                nome TEXT NOT NULL, 
                categoria TEXT DEFAULT 'Geral',
                quantidade INTEGER NOT NULL, 
                preco REAL NOT NULL)""")
    
    try:
        cursor.execute("ALTER TABLE estoque ADD COLUMN categoria TEXT DEFAULT 'Geral'")
        conexao.commit()
    except sqlite3.OperationalError:
        pass

    if request.method == "POST":
        acao = request.form.get("acao")
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

        cursor.execute(
            "INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (?, ?, ?, ?)",
            (f"Venda Mesa {mesa}: {produto} (x{qtd})", subtotal, "Receita", data_atual),
        )

      cursor.execute(
          "UPDATE caixa SET status = 'fechado', valor_final = ? WHERE status = 'aberto'",
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

  cursor.execute("SELECT * FROM financeiro ORDER BY id DESC")
  movimentacoes = cursor.fetchall()

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
      "INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (?, ?, ?, ?)",
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
        "SELECT produto, quantidade, preco FROM pedidos WHERE mesa_numero = ?",
        (mesa_numero,),
    )
    itens = cursor.fetchall()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not itens:
        conexao.close()
        return

    total_mesa = 0.0
    lista_produtos = []
    lista_formatada_historico = []

    for item in itens:
        produto, qtd, preco = item
        subtotal = float(qtd) * float(preco)
        total_mesa += subtotal
        lista_produtos.append(f"{produto} (x{qtd})")
        lista_formatada_historico.append(f"{int(qtd)}x {produto} (R$ {subtotal:.2f})")

    texto_produtos = " | ".join(lista_formatada_historico)
    cursor.execute(
        "INSERT INTO historico_fechamentos (mesa_numero, produtos_json, total, data_hora) VALUES (?, ?, ?, ?)",
        (str(mesa_numero), texto_produtos, total_mesa, data_atual)
    )

    descricao_consolidada = f"Venda Mesa {mesa_numero}: " + " + ".join(lista_produtos)
    cursor.execute(
        "INSERT INTO financeiro (descricao, valor, tipo, data) VALUES (?, ?, ?, ?)",
        (descricao_consolidada, total_mesa, "Receita", data_atual),
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


@app.route('/reimprimir_fechada')
def reimprimir_fechada():
    venda_id = request.args.get('id_venda')
    if not venda_id:
        return "Erro: Venda não selecionada", 400

    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("SELECT mesa_numero, produtos_json, total, data_hora FROM historico_fechamentos WHERE id = ?", (venda_id,))
    venda = cursor.fetchone()
    conexao.close()

    if not venda:
        return "Venda não encontrada no histórico.", 404

    return render_template(
        'cupom_reimpressao.html',
        mesa=venda[0],
        detalhes=venda[1],
        total=venda[2],
        data_hora=venda[3]
    )


@app.route('/relatorios')
def relatorios():
    filtro_tipo = request.args.get('filtro', 'mes')
    mes_atual_padrao = datetime.now().strftime('%Y-%m')
    mes_selecionado = request.args.get('mes_ano', mes_atual_padrao)
    
    conexao = sqlite3.connect("restaurante.db")
    cursor = conexao.cursor()
    
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
    cursor = conexao.cursor()
    
    cursor.execute("SELECT numero, status, praca_id FROM mesas ORDER BY numero") 
    mesas = cursor.fetchall()

    por_praca = {} 
    for mesa in mesas:
        praca = mesa[2]
        if praca not in por_praca:
            por_praca[praca] = []
        por_praca[praca].append(mesa)

    cursor.execute("SELECT * FROM estoque")
    estoque_itens = cursor.fetchall()

    cursor.execute("SELECT id, mesa_numero, total, data_hora FROM historico_fechamentos ORDER BY id DESC LIMIT 20")
    vendas_db = cursor.fetchall()
    vendas_fechadas = [{'id': v[0], 'mesa': v[1], 'total': v[2], 'hora': v[3]} for v in vendas_db]
    
    conexao.close()
    
    return render_template(
        'vendas.html', 
        mesas=mesas, 
        por_praca=por_praca, 
        estoque_itens=estoque_itens,
        vendas_fechadas=vendas_fechadas
    )


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

    cursor.execute("SELECT preco, quantidade FROM estoque WHERE nome = ?", (produto,))
    resultado = cursor.fetchone()
    
    if resultado:
        preco_unitario = resultado[0]
        estoque_atual = resultado[1]
        valor_total = preco_unitario * quantidade

        novo_estoque = estoque_atual - quantidade
        cursor.execute("UPDATE estoque SET quantidade = ? WHERE nome = ?", (novo_estoque, produto))

        descricao_venda = f"Venda Balcão: {produto} (x{quantidade}) - {pagamento}"
        cursor.execute(
            "INSERT INTO financeiro (descricao, tipo, valor) VALUES (?, 'Receita', ?)",
            (descricao_venda, valor_total)
        )
        conexao.commit()
        conexao.close()
        
        return render_template(
            'cupom_balcao.html',
            produto=produto,
            quantidade=quantidade,
            total=valor_total,
            pagamento=pagamento,
            data_hora=datetime.now().strftime("%d/%m/%Y %H:%M")
        )
    else:
        conexao.close()
        return f"<h1>ERRO!</h1> <p>O produto '<b>{produto}</b>' não existe no estoque.</p>"
    

# ==========================================
# ROTAS DE CONFIGURAÇÃO E USUÁRIOS (ÚNICA)
# ==========================================
@app.route("/configuracao")
def configuracao():
    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome FROM usuarios")
    lista_usuarios = cursor.fetchall()
    conexao.close()
    return render_template("configuracao.html", usuarios=lista_usuarios)


@app.route('/salvar_novo_usuario', methods=['POST'])
def salvar_novo_usuario():
    nome = request.form.get('nome')
    senha = request.form.get('senha')

    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            senha TEXT
        )
    """)
    cursor.execute("INSERT INTO usuarios (nome, senha) VALUES (?, ?)", (nome, senha))
    conexao.commit()
    conexao.close()
        
    return redirect(url_for('configuracao'))


@app.route('/excluir_usuario/<int:id_usuario>', methods=['POST'])
def excluir_usuario(id_usuario):
    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_usuario,))
    conexao.commit()
    conexao.close()
    return redirect(url_for('configuracao'))


@app.route('/imprimir_cupom')
def imprimir_cupom():
    numero_mesa = request.args.get('numero_mesa')
    if not numero_mesa:
        return "Erro: Nenhuma mesa selecionada", 400

    conexao = sqlite3.connect("restaurante.db")
    cursor = conexao.cursor()
    
    cursor.execute(
        "SELECT produto, quantidade, preco FROM pedidos WHERE mesa_numero = ?",
        (numero_mesa,)
    )
    itens = cursor.fetchall()
    conexao.close()
    
    total_venda = 0.0
    pedidos_formatados = []
    
    for item in itens:
        nome_produto = item[0]
        qtd = float(item[1])
        preco = float(item[2])
        subtotal = qtd * preco
        
        total_venda += subtotal
        
        pedidos_formatados.append({
            'produto': nome_produto,
            'quantidade': int(qtd),
            'subtotal': subtotal
        })
        
    return render_template(
        'cupom.html', 
        numero_mesa=numero_mesa, 
        pedidos=pedidos_formatados, 
        total=total_venda,
        data_hora=datetime.now().strftime("%d/%m/%Y %H:%M")
    )

@app.route("/sair")
def sair():
    return render_template("sair.html")
if __name__ == "__main__":
  app.run(debug=True)