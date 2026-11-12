from flask import Flask, render_template, request, redirect, flash, session
import mysql.connector
from config import DB_CONFIG
from datetime import datetime

app = Flask(__name__)
app.secret_key = "restaurante_secreto_2026" # Chave para as sessões e mensagens flash

# Função de conexão com o banco de dados
def conectar():
    return mysql.connector.connect(**DB_CONFIG)

# ==========================================
# ROTAS DE AUTENTICAÇÃO (LOGIN/LOGOUT)
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario_input = request.form["login"]
        senha = request.form["senha"]
        try:
            conexao = conectar()
            cursor = conexao.cursor(dictionary=True)
            
            # Voltamos a usar o status, pois você criou a coluna no banco
            sql = """
                SELECT * FROM usuario 
                WHERE login = %s 
                AND senha = %s 
                AND status = 'Ativo'
            """
            cursor.execute(sql, (usuario_input, senha))
            usuario = cursor.fetchone()
            cursor.close()
            conexao.close()

            if usuario:
                session["id_usuario"] = usuario["id_usuario"]
                session["nome"] = usuario["nome"]
                session["perfil"] = usuario["perfil"]
                flash("Login realizado com sucesso!", "sucesso")
                return redirect("/")
            else:
                flash("Usuário ou senha inválidos.", "erro")
                return redirect("/login")
        except Exception as erro:
            flash(f"Erro ao realizar login: {erro}", "erro")
            return redirect("/login")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "sucesso")
    return redirect("/login")

# ==========================================
# ROTA INICIAL (PAINEL)
# ==========================================

@app.route("/")
def index():
    if "id_usuario" not in session:
        return redirect("/login")
        
    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        
        cursor.execute("SELECT COUNT(*) AS total FROM cliente")
        total_clientes = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) AS total FROM prato")
        total_pratos = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) AS total FROM prato WHERE status = 'Disponível'")
        total_disponiveis = cursor.fetchone()["total"]
        
        cursor.execute("SELECT COUNT(*) AS total FROM pedido WHERE status = 'Em Preparo'")
        total_pedidos = cursor.fetchone()["total"]
        
        cursor.close()
        conexao.close()
        
        return render_template("index.html", 
                               total_clientes=total_clientes,
                               total_pratos=total_pratos,
                               total_disponiveis=total_disponiveis,
                               total_pedidos=total_pedidos)
    except Exception as erro:
        flash(f"Erro ao carregar página inicial: {erro}", "erro")
        return render_template("index.html", total_clientes=0, total_pratos=0, total_disponiveis=0, total_pedidos=0)

# ==========================================
# CRUD DE CLIENTES
# ==========================================

@app.route("/clientes")
def listar_clientes():
    if "id_usuario" not in session: return redirect("/login")
    try:
        pesquisa = request.args.get("pesquisa", "")
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        
        if pesquisa:
            sql = "SELECT * FROM cliente WHERE nome LIKE %s OR email LIKE %s OR telefone LIKE %s ORDER BY nome"
            valor = f"%{pesquisa}%"
            cursor.execute(sql, (valor, valor, valor))
        else:
            cursor.execute("SELECT * FROM cliente ORDER BY nome")
            
        clientes = cursor.fetchall()
        cursor.close()
        conexao.close()
        return render_template("clientes.html", clientes=clientes, pesquisa=pesquisa)
    except Exception as erro:
        flash(f"Erro ao listar clientes: {erro}", "erro")
        return redirect("/")

@app.route("/clientes/novo")
def formulario_cliente():
    if "id_usuario" not in session: return redirect("/login")
    return render_template("cliente_form.html")

@app.route("/clientes/cadastrar", methods=["POST"])
def cadastrar_cliente():
    if "id_usuario" not in session: return redirect("/login")
    try:
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        email = request.form["email"]
        
        if len(nome.strip()) < 3:
            flash("O nome do cliente deve ter pelo menos 3 caracteres.", "erro")
            return redirect("/clientes/novo")
            
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO cliente (nome, telefone, email) VALUES (%s, %s, %s)"
        cursor.execute(sql, (nome, telefone, email))
        conexao.commit()
        cursor.close()
        conexao.close()
        
        flash("Cliente cadastrado com sucesso!", "sucesso")
        return redirect("/clientes")
    except Exception as erro:
        flash(f"Erro ao cadastrar cliente: {erro}", "erro")
        return redirect("/clientes/novo")

@app.route("/clientes/editar/<int:id_cliente>")
def editar_cliente(id_cliente):
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cliente WHERE id_cliente = %s", (id_cliente,))
        cliente = cursor.fetchone()
        cursor.close()
        conexao.close()
        return render_template("cliente_editar.html", cliente=cliente)
    except Exception as erro:
        flash(f"Erro ao carregar cliente: {erro}", "erro")
        return redirect("/clientes")

@app.route("/clientes/atualizar/<int:id_cliente>", methods=["POST"])
def atualizar_cliente(id_cliente):
    if "id_usuario" not in session: return redirect("/login")
    try:
        nome = request.form["nome"]
        telefone = request.form["telefone"]
        email = request.form["email"]
        
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE cliente SET nome = %s, telefone = %s, email = %s WHERE id_cliente = %s"
        cursor.execute(sql, (nome, telefone, email, id_cliente))
        conexao.commit()
        cursor.close()
        conexao.close()
        
        flash("Cliente atualizado com sucesso!", "sucesso")
        return redirect("/clientes")
    except Exception as erro:
        flash(f"Erro ao atualizar cliente: {erro}", "erro")
        return redirect("/clientes")

@app.route("/clientes/excluir/<int:id_cliente>")
def excluir_cliente(id_cliente):
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM cliente WHERE id_cliente = %s", (id_cliente,))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Cliente excluído com sucesso!", "sucesso")
        return redirect("/clientes")
    except Exception as erro:
        flash("Não foi possível excluir o cliente. Verifique se ele possui pedidos cadastrados.", "erro")
        return redirect("/clientes")

# ==========================================
# CRUD DE PRATOS (CARDÁPIO)
# ==========================================

@app.route("/pratos")
def listar_pratos():
    if "id_usuario" not in session: return redirect("/login")
    try:
        pesquisa = request.args.get("pesquisa", "")
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        
        if pesquisa:
            sql = "SELECT * FROM prato WHERE nome LIKE %s OR categoria LIKE %s OR status LIKE %s ORDER BY nome"
            valor = f"%{pesquisa}%"
            cursor.execute(sql, (valor, valor, valor))
        else:
            cursor.execute("SELECT * FROM prato ORDER BY nome")
            
        pratos = cursor.fetchall()
        cursor.close()
        conexao.close()
        return render_template("pratos.html", pratos=pratos, pesquisa=pesquisa)
    except Exception as erro:
        flash(f"Erro ao listar pratos: {erro}", "erro")
        return redirect("/")

@app.route("/pratos/novo")
def formulario_prato():
    if "id_usuario" not in session: return redirect("/login")
    return render_template("prato_form.html")

@app.route("/pratos/cadastrar", methods=["POST"])
def cadastrar_prato():
    if "id_usuario" not in session: return redirect("/login")
    try:
        nome = request.form["nome"]
        descricao = request.form["descricao"]
        preco = request.form["preco"]
        categoria = request.form["categoria"]
        
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO prato (nome, descricao, preco, categoria, status) VALUES (%s, %s, %s, %s, 'Disponível')"
        cursor.execute(sql, (nome, descricao, preco, categoria))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Prato cadastrado com sucesso!", "sucesso")
        return redirect("/pratos")
    except Exception as erro:
        flash(f"Erro ao cadastrar prato: {erro}", "erro")
        return redirect("/pratos/novo")

@app.route("/pratos/editar/<int:id_prato>")
def editar_prato(id_prato):
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM prato WHERE id_prato = %s", (id_prato,))
        prato = cursor.fetchone()
        cursor.close()
        conexao.close()
        return render_template("prato_editar.html", prato=prato)
    except Exception as erro:
        flash(f"Erro ao carregar prato: {erro}", "erro")
        return redirect("/pratos")

@app.route("/pratos/atualizar/<int:id_prato>", methods=["POST"])
def atualizar_prato(id_prato):
    if "id_usuario" not in session: return redirect("/login")
    try:
        nome = request.form["nome"]
        descricao = request.form["descricao"]
        preco = request.form["preco"]
        categoria = request.form["categoria"]
        status = request.form["status"]
        
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE prato SET nome = %s, descricao = %s, preco = %s, categoria = %s, status = %s WHERE id_prato = %s"
        cursor.execute(sql, (nome, descricao, preco, categoria, status, id_prato))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Prato atualizado com sucesso!", "sucesso")
        return redirect("/pratos")
    except Exception as erro:
        flash(f"Erro ao atualizar prato: {erro}", "erro")
        return redirect("/pratos")

@app.route("/pratos/excluir/<int:id_prato>")
def excluir_prato(id_prato):
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM prato WHERE id_prato = %s", (id_prato,))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Prato excluído com sucesso!", "sucesso")
        return redirect("/pratos")
    except Exception as erro:
        flash("Não foi possível excluir o prato. Verifique se ele possui pedidos cadastrados.", "erro")
        return redirect("/pratos")

# ==========================================
# CRUD DE FUNCIONÁRIOS
# ==========================================

@app.route("/funcionarios")
def listar_funcionarios():
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM funcionario ORDER BY nome")
        funcionarios = cursor.fetchall()
        cursor.close()
        conexao.close()
        return render_template("funcionarios.html", funcionarios=funcionarios)
    except Exception as erro:
        flash(f"Erro ao listar funcionários: {erro}", "erro")
        return redirect("/")

@app.route("/funcionarios/novo")
def formulario_funcionario():
    if "id_usuario" not in session: return redirect("/login")
    return render_template("funcionario_form.html")

@app.route("/funcionarios/cadastrar", methods=["POST"])
def cadastrar_funcionario():
    if "id_usuario" not in session: return redirect("/login")
    try:
        nome = request.form["nome"]
        cargo = request.form["cargo"]
        email = request.form["email"]
        
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO funcionario (nome, cargo, email) VALUES (%s, %s, %s)"
        cursor.execute(sql, (nome, cargo, email))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Funcionário cadastrado com sucesso!", "sucesso")
        return redirect("/funcionarios")
    except Exception as erro:
        flash(f"Erro ao cadastrar funcionário: {erro}", "erro")
        return redirect("/funcionarios/novo")

@app.route("/funcionarios/editar/<int:id_funcionario>")
def editar_funcionario(id_funcionario):
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute("SELECT * FROM funcionario WHERE id_funcionario = %s", (id_funcionario,))
        funcionario = cursor.fetchone()
        cursor.close()
        conexao.close()
        return render_template("funcionario_editar.html", funcionario=funcionario)
    except Exception as erro:
        flash(f"Erro ao carregar funcionário: {erro}", "erro")
        return redirect("/funcionarios")

@app.route("/funcionarios/atualizar/<int:id_funcionario>", methods=["POST"])
def atualizar_funcionario(id_funcionario):
    if "id_usuario" not in session: return redirect("/login")
    try:
        nome = request.form["nome"]
        cargo = request.form["cargo"]
        email = request.form["email"]
        
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE funcionario SET nome = %s, cargo = %s, email = %s WHERE id_funcionario = %s"
        cursor.execute(sql, (nome, cargo, email, id_funcionario))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Funcionário atualizado com sucesso!", "sucesso")
        return redirect("/funcionarios")
    except Exception as erro:
        flash(f"Erro ao atualizar funcionário: {erro}", "erro")
        return redirect("/funcionarios")

@app.route("/funcionarios/excluir/<int:id_funcionario>")
def excluir_funcionario(id_funcionario):
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM funcionario WHERE id_funcionario = %s", (id_funcionario,))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Funcionário excluído com sucesso!", "sucesso")
        return redirect("/funcionarios")
    except Exception as erro:
        flash("Não foi possível excluir o funcionário. Verifique se ele possui pedidos registrados.", "erro")
        return redirect("/funcionarios")

# ==========================================
# CRUD DE PEDIDOS
# ==========================================

@app.route("/pedidos")
def listar_pedidos():
    if "id_usuario" not in session: return redirect("/login")
    try:
        status = request.args.get("status", "")
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        
        sql = """
            SELECT 
                p.id_pedido, 
                c.nome AS cliente, 
                pr.nome AS prato, 
                f.nome AS funcionario, 
                p.data_pedido, 
                p.quantidade, 
                p.status 
            FROM pedido p
            INNER JOIN cliente c ON p.id_cliente = c.id_cliente
            INNER JOIN prato pr ON p.id_prato = pr.id_prato
            INNER JOIN funcionario f ON p.id_funcionario = f.id_funcionario
        """
        
        if status:
            sql += " WHERE p.status = %s ORDER BY p.id_pedido DESC"
            cursor.execute(sql, (status,))
        else:
            sql += " ORDER BY p.id_pedido DESC"
            cursor.execute(sql)
            
        pedidos = cursor.fetchall()
        cursor.close()
        conexao.close()
        return render_template("pedidos.html", pedidos=pedidos, status=status)
    except Exception as erro:
        flash(f"Erro ao listar pedidos: {erro}", "erro")
        return redirect("/")

@app.route("/pedidos/novo")
def formulario_pedido():
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM cliente ORDER BY nome")
        clientes = cursor.fetchall()
        
        # Só mostra pratos disponíveis
        cursor.execute("SELECT * FROM prato WHERE status = 'Disponível' ORDER BY nome")
        pratos = cursor.fetchall()
        
        cursor.execute("SELECT * FROM funcionario ORDER BY nome")
        funcionarios = cursor.fetchall()
        
        cursor.close()
        conexao.close()
        return render_template("pedido_form.html", clientes=clientes, pratos=pratos, funcionarios=funcionarios)
    except Exception as erro:
        flash(f"Erro ao carregar formulário: {erro}", "erro")
        return redirect("/pedidos")

@app.route("/pedidos/cadastrar", methods=["POST"])
def cadastrar_pedido():
    if "id_usuario" not in session: return redirect("/login")
    try:
        id_cliente = request.form["id_cliente"]
        id_prato = request.form["id_prato"]
        id_funcionario = request.form["id_funcionario"]
        data_pedido = request.form["data_pedido"]
        quantidade = request.form["quantidade"]
        
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        
        # Validação 1: Data não pode ser no passado
        data_hoje = datetime.now().strftime('%Y-%m-%d')
        if data_pedido < data_hoje:
            flash("A data do pedido não pode ser no passado.", "erro")
            return redirect("/pedidos/novo")

        # Validação 2: Verificar se o prato está disponível
        cursor.execute("SELECT status FROM prato WHERE id_prato = %s", (id_prato,))
        prato = cursor.fetchone()
        if prato is None or prato["status"] != "Disponível":
            flash("Este prato não está disponível para pedido.", "erro")
            cursor.close()
            conexao.close()
            return redirect("/pedidos/novo")

        # Inserir Pedido
        sql = """
            INSERT INTO pedido (id_cliente, id_prato, id_funcionario, data_pedido, quantidade, status) 
            VALUES (%s, %s, %s, %s, %s, 'Em Preparo')
        """
        cursor.execute(sql, (id_cliente, id_prato, id_funcionario, data_pedido, quantidade))
        
        # Opcional: Se for um prato que acaba no estoque, daria para mudar o status aqui.
        # Mas em restaurantes o prato continua no menu.
        
        conexao.commit()
        cursor.close()
        conexao.close()
        
        flash("Pedido registrado com sucesso!", "sucesso")
        return redirect("/pedidos")
    except Exception as erro:
        flash(f"Erro ao registrar pedido: {erro}", "erro")
        return redirect("/pedidos/novo")

@app.route("/pedidos/entregar/<int:id_pedido>")
def entregar_pedido(id_pedido):
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("UPDATE pedido SET status = 'Entregue' WHERE id_pedido = %s", (id_pedido,))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Pedido marcado como Entregue!", "sucesso")
        return redirect("/pedidos")
    except Exception as erro:
        flash(f"Erro ao atualizar pedido: {erro}", "erro")
        return redirect("/pedidos")

@app.route("/pedidos/cancelar/<int:id_pedido>")
def cancelar_pedido(id_pedido):
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("UPDATE pedido SET status = 'Cancelado' WHERE id_pedido = %s", (id_pedido,))
        conexao.commit()
        cursor.close()
        conexao.close()
        flash("Pedido cancelado com sucesso.", "aviso")
        return redirect("/pedidos")
    except Exception as erro:
        flash(f"Erro ao cancelar pedido: {erro}", "erro")
        return redirect("/pedidos")

# ==========================================
# PEDIDOS ATRASADOS (Em Preparo há muito tempo)
# ==========================================

@app.route("/pedidos/atrasados")
def listar_pedidos_atrasados():
    if "id_usuario" not in session: return redirect("/login")
    try:
        conexao = conectar()
        cursor = conexao.cursor(dictionary=True)
        
        # Supondo que um pedido "Em Preparo" não deve demorar mais de 1 dia (simulação)
        sql = """
            SELECT 
                p.id_pedido, 
                c.nome AS cliente, 
                pr.nome AS prato, 
                f.nome AS funcionario, 
                p.data_pedido, 
                DATEDIFF(CURDATE(), p.data_pedido) AS dias_espera,
                p.status 
            FROM pedido p
            INNER JOIN cliente c ON p.id_cliente = c.id_cliente
            INNER JOIN prato pr ON p.id_prato = pr.id_prato
            INNER JOIN funcionario f ON p.id_funcionario = f.id_funcionario
            WHERE p.status = 'Em Preparo' 
            AND p.data_pedido < CURDATE()
            ORDER BY p.data_pedido
        """
        cursor.execute(sql)
        pedidos = cursor.fetchall()
        cursor.close()
        conexao.close()
        return render_template("pedidos_atrasados.html", pedidos=pedidos)
    except Exception as erro:
        flash(f"Erro ao listar pedidos atrasados: {erro}", "erro")
        return redirect("/pedidos")

if __name__ == "__main__":
    app.run(debug=True)