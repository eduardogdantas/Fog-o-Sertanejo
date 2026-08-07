from datetime import datetime
from flask import Flask, redirect, render_template, request, url_for, jsonify, session
from flask_cors import CORS
import sqlite3
import re

app = Flask(__name__)
app.secret_key = "chave_super_secreta_restaurante"
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)


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
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN permissao TEXT DEFAULT 'comum'")
        cursor.execute("UPDATE usuarios SET permissao = 'admin' WHERE nome = 'admin'")
    except sqlite3.OperationalError:
        pass

    conexao.commit()
    conexao.close()

criar_tabelas()


@app.route("/")
def home():
    if not session.get("logado"):
        return redirect(url_for("login"))

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
@app.route("/ver_mesa/<int:numero_mesa>")
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

    cursor.execute("SELECT preco, quantidade FROM estoque WHERE nome = ?", (produto,))
    resultado = cursor.fetchone()
    
    if resultado:
        preco_unitario = resultado[0]
        estoque_atual = resultado[1]
        
        novo_estoque = estoque_atual - quantidade
        if novo_estoque < 0:
            novo_estoque = 0 
            
        cursor.execute("UPDATE estoque SET quantidade = ? WHERE nome = ?", (novo_estoque, produto))
    else:
        preco_unitario = 0.0

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
                nome_prod = request.form.get("nome_texto", "").strip()
                
                cursor.execute("SELECT id, quantidade FROM estoque WHERE LOWER(nome) = LOWER(?)", (nome_prod,))
                produto_existente = cursor.fetchone()
                
                if produto_existente:
                    produto_id = produto_existente[0]
                    quantidade_antiga = produto_existente[1] if produto_existente[1] else 0
                    quantidade_nova = quantidade_antiga + int(qtd)
                    
                    cursor.execute(
                        "UPDATE estoque SET quantidade = ?, preco = ? WHERE id = ?",
                        (quantidade_nova, preco, produto_id)
                    )
                else:
                    cursor.execute(
                        "INSERT INTO estoque (nome, quantidade, preco) VALUES (?, ?, ?)",
                        (nome_prod, int(qtd), preco),
                    )
                    
            elif acao == "remover":
                cursor.execute("DELETE FROM estoque WHERE id = ?", (identificador,))
                
            elif acao == "alterar":
                nome_prod = request.form.get("nome_texto", "").strip()
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
            # Se o usuário deixar vazio, o float("") daria erro, 
            # então pegamos o valor e garantimos que vira 0.0 se estiver vazio
            valor_raw = request.form.get("valor", "")
            try:
                # Substitui vírgula por ponto para não quebrar o cálculo
                valor = float(valor_raw.replace(",", ".")) if valor_raw.strip() != "" else 0.0
            except ValueError:
                valor = 0.0
            
            data_hora_agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute(
                "INSERT INTO caixa (status, valor_inicial, data) VALUES ('aberto', ?, ?)",
                (valor, data_hora_agora),
            )
            conexao.commit()

        elif acao == "fechar":
            conexao = sqlite3.connect("restaurante.db")
            cursor = conexao.cursor()

            # 1. Pega o ID e a data/hora exata em que ESTE caixa foi aberto
            cursor.execute("SELECT id, data FROM caixa WHERE status = 'aberto' ORDER BY id DESC LIMIT 1")
            caixa_aberto = cursor.fetchone()

            if caixa_aberto:
                caixa_id = caixa_aberto[0]
                data_hora_abertura = caixa_aberto[1] # Ex: "2026-08-06 21:50:00"

                # Se por acaso a data do caixa estiver vazia, usamos o horário atual de segurança
                if not data_hora_abertura:
                    data_hora_abertura = datetime.now().strftime("%Y-%m-%d 00:00:00")

                # 2. Soma SOMENTE as receitas geradas APÓS a hora que este caixa abriu
                cursor.execute(
                    "SELECT SUM(valor) FROM financeiro WHERE tipo = 'Receita' AND data >= ?", 
                    (data_hora_abertura,)
                )
                resultado = cursor.fetchone()[0]
                total_vendas = float(resultado) if resultado else 0.0

                # 3. Atualiza o caixa atual com o valor correto do turno
                cursor.execute(
                    "UPDATE caixa SET status = 'fechado', valor_final = ? WHERE id = ?", 
                    (total_vendas, caixa_id)
                )

            # Limpa os pedidos das mesas
            cursor.execute("DELETE FROM pedidos")
            cursor.execute("UPDATE mesas SET status = 'Disponivel'")
            
            conexao.commit()
            conexao.close()

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
    origem = request.args.get("origem")

    registrar_venda_financeiro(numero_mesa)

    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM pedidos WHERE mesa_numero = ?", (numero_mesa,))
    cursor.execute(
        "UPDATE mesas SET status = 'Disponivel' WHERE numero = ?",
        (numero_mesa,),
    )
    conexao.commit()
    conexao.close()

    if origem == "vendas":
        return redirect(url_for("vendas"))
    elif origem == "home":
        return redirect(url_for("vendas"))

    if request.referrer:
        return redirect(request.referrer)

    return redirect(url_for("vendas"))


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
    filtro_tipo = request.args.get('filtro', 'dia') 
    
    data_atual_padrao = datetime.now().strftime('%Y-%m-%d')
    mes_atual_padrao = datetime.now().strftime('%Y-%m')
    semana_atual_padrao = datetime.now().strftime('%G-W%V')
    
    data_selecionada = request.args.get('data_escolhida', data_atual_padrao)
    mes_selecionado = request.args.get('mes_ano', mes_atual_padrao)
    semana_selecionada = request.args.get('semana_escolhida', semana_atual_padrao)
    
    conexao = sqlite3.connect("restaurante.db")
    cursor = conexao.cursor()
    
    if filtro_tipo == 'mes':
        termo_busca = f"{mes_selecionado}%"
        cursor.execute("SELECT id, descricao, tipo, valor FROM financeiro WHERE tipo = 'Receita' AND data LIKE ? ORDER BY id DESC", (termo_busca,))
        
    elif filtro_tipo == 'semana':
        try:
            ano_str, semana_str = semana_selecionada.split('-W')
            inicio_semana = datetime.strptime(f'{ano_str}-W{semana_str}-1', "%G-W%V-%u").strftime('%Y-%m-%d 00:00:00')
            fim_semana = datetime.strptime(f'{ano_str}-W{semana_str}-7', "%G-W%V-%u").strftime('%Y-%m-%d 23:59:59')
        except ValueError:
            inicio_semana = "1900-01-01 00:00:00"
            fim_semana = "2100-01-01 23:59:59"
            
        cursor.execute("""
            SELECT id, descricao, tipo, valor 
            FROM financeiro 
            WHERE tipo = 'Receita' AND data >= ? AND data <= ? 
            ORDER BY id DESC
        """, (inicio_semana, fim_semana))
        
    else: # dia
        termo_busca = f"{data_selecionada}%"
        cursor.execute("SELECT id, descricao, tipo, valor FROM financeiro WHERE tipo = 'Receita' AND data LIKE ? ORDER BY id DESC", (termo_busca,))
        
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
        mes_selecionado=mes_selecionado,
        data_selecionada=data_selecionada,
        semana_selecionada=semana_selecionada
    )


@app.route('/vendas')
def vendas():
    if not session.get("logado"):
        return redirect(url_for("login"))

    conexao = sqlite3.connect("restaurante.db")
    cursor = conexao.cursor()
    
    # Busca as mesas cadastradas
    cursor.execute("SELECT numero, status, praca_id FROM mesas ORDER BY numero") 
    mesas_raw = cursor.fetchall()

    # Recalcula dinamicamente se a mesa está ocupada com base nos pedidos ativos
    mesas = []
    for m in mesas_raw:
        num_mesa = m[0]
        praca_id = m[2]
        
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE CAST(mesa_numero AS TEXT) = CAST(? AS TEXT)", (num_mesa,))
        tem_pedidos = cursor.fetchone()[0] > 0
        
        status_atualizado = "Ocupada" if tem_pedidos else "Disponivel"
        
        # Opcional: Atualiza também no banco para manter sincronizado
        cursor.execute("UPDATE mesas SET status = ? WHERE numero = ?", (status_atualizado, num_mesa))
        
        mesas.append((num_mesa, status_atualizado, praca_id))
    
    conexao.commit()

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

    
@app.route("/configuracao")
def configuracao():
    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome, permissao FROM usuarios")
    lista_usuarios = cursor.fetchall()
    conexao.close()
    return render_template("configuracao.html", usuarios=lista_usuarios)


@app.route('/salvar_novo_usuario', methods=['POST'])
def salvar_novo_usuario():
    if session.get("usuario_nome") != "admin" and session.get("permissao") != "admin":
        return "Erro: Apenas o administrador pode adicionar usuários.", 403

    nome = request.form.get('nome')
    senha = request.form.get('senha')
    permissao = request.form.get('permissao', 'comum')

    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO usuarios (nome, senha, permissao) VALUES (?, ?, ?)", (nome, senha, permissao))
    conexao.commit()
    conexao.close()
        
    return redirect(url_for('configuracao'))


@app.route('/excluir_usuario/<int:id_usuario>', methods=['POST'])
def excluir_usuario(id_usuario):
    if session.get("usuario_nome") != "admin" and session.get("permissao") != "admin":
        return "Erro: Apenas o administrador pode excluir usuários.", 403

    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id_usuario,))
    conexao.commit()
    conexao.close()
    return redirect(url_for('configuracao'))


@app.route('/alternar_permissao/<int:id_usuario>', methods=['POST'])
def alternar_permissao(id_usuario):
    if session.get("usuario_nome") != "admin" and session.get("permissao") != "admin":
        return "Erro: Sem permissão.", 403

    nova_permissao = request.form.get('permissao')
    
    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("UPDATE usuarios SET permissao = ? WHERE id = ?", (nova_permissao, id_usuario))
    conexao.commit()
    conexao.close()
    return redirect(url_for('configuracao'))


def criar_usuario_admin():
    conexao = conectar_db()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT * FROM usuarios WHERE nome = 'admin'")
    admin_existe = cursor.fetchone()
    
    if not admin_existe:
        cursor.execute("INSERT INTO usuarios (nome, senha) VALUES ('admin', '1234')")
        conexao.commit()
        print("Usuário administrador criado com sucesso! Login: admin / Senha: 1234")
        
    conexao.close()

criar_tabelas()
criar_usuario_admin()


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


@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login():
    # O navegador envia um OPTIONS antes do POST. Precisamos responder 200 OK para liberar.
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response, 200

    # Lógica normal do seu login
    dados = request.get_json() or {}
    usuario = dados.get('usuario', '')
    senha = dados.get('senha', '')

    if usuario == 'eduardo' and senha == '123':
        return jsonify({"sucesso": True, "mensagem": "Logado com sucesso"}), 200
    else:
        return jsonify({"sucesso": False, "mensagem": "Usuário ou senha inválidos"}), 401


# ==========================================
# APIs PARA O FLUTTER
# ==========================================
@app.route('/api/comandas-ativas')
def comandas_ativas():
    conexao = conectar_db()
    cursor = conexao.cursor()
    
    try:
        cursor.execute("SELECT DISTINCT mesa_numero FROM pedidos")
        mesas_com_pedidos = cursor.fetchall()
    except sqlite3.OperationalError:
        conexao.close()
        return jsonify({'comandas': []})
    
    comandas = []
    
    for m in mesas_com_pedidos:
        num_mesa_raw = m[0]
        if num_mesa_raw is None:
            continue
            
        cursor.execute(
            "SELECT produto, quantidade, preco FROM pedidos WHERE CAST(mesa_numero AS TEXT) = CAST(? AS TEXT)", 
            (num_mesa_raw,)
        )
        pedidos = cursor.fetchall()
        
        total_mesa = 0.0
        lista_itens = []
        
        for item in pedidos:
            nome_prod, qtd, preco = item
            subtotal = float(qtd or 0) * float(preco or 0)
            total_mesa += subtotal
            lista_itens.append({
                'produto': nome_prod,          # Nome do produto consumido
                'quantidade': int(qtd or 1),    # Quantidade pedida
                'preco': float(preco or 0),     # Preço unitário
                'subtotal': subtotal            # Subtotal do item
            })
            
        comandas.append({
            'numero_mesa': str(num_mesa_raw),
            'total': total_mesa,
            'itens': lista_itens
        })
        
    conexao.close()
    return jsonify({'comandas': comandas})


@app.route('/api/historico-vendas')
def obter_historico_vendas():
    data_escolhida = request.args.get('data')
    if not data_escolhida:
        data_escolhida = datetime.now().strftime('%Y-%m-%d')

    conexao = conectar_db()
    cursor = conexao.cursor()
    
    cursor.execute("""
        SELECT id, mesa_numero, total, data_hora 
        FROM historico_fechamentos 
        WHERE data_hora LIKE ? 
        ORDER BY id DESC
    """, (f"{data_escolhida}%",))
    
    vendas_db = cursor.fetchall()
    conexao.close()

    resultado = []
    for v in vendas_db:
        hora_formatada = v[3].split(' ')[1] if ' ' in v[3] else v[3]
        resultado.append({
            'id': v[0],
            'mesa': v[1],
            'total': f"{v[2]:.2f}",
            'hora': hora_formatada
        })

    return jsonify({'vendas': resultado})


@app.route('/api/fazer_pedido', methods=['POST'])
def api_fazer_pedido():
    dados = request.get_json()
    if not dados:
        return jsonify({"erro": "Nenhum dado enviado."}), 400

    numero_mesa = dados.get('numero_mesa')
    nome_produto = dados.get('produto')
    quantidade_pedida = int(dados.get('quantidade', 1))

    conexao = conectar_db()
    cursor = conexao.cursor()

    try:
        cursor.execute("SELECT id, preco, quantidade FROM estoque WHERE nome = ?", (nome_produto,))
        resultado = cursor.fetchone()

        if not resultado:
            conexao.close()
            return jsonify({"erro": "Produto não encontrado no cardápio."}), 404

        produto_id, preco_unitario, estoque_atual = resultado

        if estoque_atual < quantidade_pedida:
            conexao.close()
            return jsonify({"erro": f"Estoque insuficiente. Restam apenas {estoque_atual} unidades."}), 400

        novo_estoque = estoque_atual - quantidade_pedida
        cursor.execute("UPDATE estoque SET quantidade = ? WHERE id = ?", (novo_estoque, produto_id))

        cursor.execute(
            "INSERT INTO pedidos (mesa_numero, produto, quantidade, preco) VALUES (?, ?, ?, ?)",
            (str(numero_mesa), nome_produto, quantidade_pedida, preco_unitario)
        )

        cursor.execute(
            "UPDATE mesas SET status = 'Ocupada' WHERE numero = ?",
            (str(numero_mesa),)
        )

        conexao.commit()
        conexao.close()

        return jsonify({
            "mensagem": "Pedido registrado com sucesso!",
            "novo_estoque": novo_estoque
        }), 200

    except Exception as e:
        conexao.rollback()
        conexao.close()
        return jsonify({"erro": "Erro interno ao processar o pedido.", "detalhes": str(e)}), 500


@app.route('/api/produtos', methods=['GET'])
def api_listar_produtos():
    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome, preco, quantidade FROM estoque")
    produtos_db = cursor.fetchall()
    conexao.close()

    lista_produtos = []
    for p in produtos_db:
        lista_produtos.append({
            "id": p[0],
            "nome": p[1],
            "preco": p[2],
            "quantidade": p[3]
        })

    return jsonify({"produtos": lista_produtos}), 200


@app.route('/api/mesas', methods=['GET'])
def get_mesas():
    conexao = conectar_db()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT numero, status FROM mesas ORDER BY numero")
    mesas_db = cursor.fetchall()
    
    lista_mesas = []
    for m in mesas_db:
        num_mesa = m[0]
        
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE CAST(mesa_numero AS TEXT) = CAST(? AS TEXT)", (num_mesa,))
        tem_pedidos = cursor.fetchone()[0] > 0
        
        status_real = "Ocupada" if tem_pedidos else "Disponível"
        is_disponivel = not tem_pedidos
        
        lista_mesas.append({
            "numero": num_mesa,
            "status": status_real,
            "disponivel": is_disponivel
        })
        
    conexao.close()
    return jsonify({"mesas": lista_mesas}), 200


@app.route("/sair")
def sair():
    session.clear() 
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)