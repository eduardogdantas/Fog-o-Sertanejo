from flask import Flask, render_template, redirect, url_for, request
import sqlite3

app = Flask(__name__)

def conectar_db():
    return sqlite3.connect('restaurante.db')

@app.route("/")
def home():
    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute('SELECT numero, status FROM mesas')
    todas_as_mesas = cursor.fetchall() 
    conexao.close()
    return render_template("index.html", mesas=todas_as_mesas)

@app.route("/mesa/<int:numero_mesa>")
def ver_mesa(numero_mesa):
    conexao = conectar_db()
    cursor = conexao.cursor()
    
    # Busca a mesa
    cursor.execute('SELECT numero, status FROM mesas WHERE numero = ?', (numero_mesa,))
    mesa_atual = cursor.fetchone()
    
    # Busca os pedidos DESSA mesa específica
    cursor.execute('SELECT produto, quantidade FROM pedidos WHERE mesa_numero = ?', (numero_mesa,))
    pedidos_da_mesa = cursor.fetchall()
    
    conexao.close()
    
    # Envia a mesa e a lista de pedidos para o HTML
    return render_template("mesa.html", mesa=mesa_atual, pedidos=pedidos_da_mesa)

@app.route("/mudar_status/<int:numero_mesa>/<novo_status>")
def mudar_status(numero_mesa, novo_status):
    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute('UPDATE mesas SET status = ? WHERE numero = ?', (novo_status, numero_mesa))
    conexao.commit()
    conexao.close()
    return redirect(url_for('ver_mesa', numero_mesa=numero_mesa))

@app.route("/adicionar_pedido/<int:numero_mesa>", methods=["POST"])
def adicionar_pedido(numero_mesa):
    produto = request.form.get("produto")
    quantidade = request.form.get("quantidade")
    
    # Isso vai aparecer no seu terminal (tela preta)
    print(f"DEBUG: Recebi Produto='{produto}', Quantidade='{quantidade}'")

    if not produto:
        return "Erro: O campo produto não foi enviado!", 400

    conexao = conectar_db()
    cursor = conexao.cursor()
    cursor.execute('INSERT INTO pedidos (mesa_numero, produto, quantidade) VALUES (?, ?, ?)', 
                   (numero_mesa, produto, quantidade))
    conexao.commit()
    conexao.close()

    return redirect(url_for('ver_mesa', numero_mesa=numero_mesa))
if __name__ == "__main__":
    app.run(debug=True)