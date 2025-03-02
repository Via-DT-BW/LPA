import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import pyodbc
import pandas as pd
from datetime import datetime


app = Flask(__name__)
app.secret_key = 'secretkeysparepartscroston'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(BASE_DIR, "connections", "settings.json")

# Carregar configurações de conexão do banco de dados
with open(settings_path, "r") as f:
    settings = json.load(f)
connection_string = settings[0]["connection_string_db_teste_jose"]

def get_db_connection():
    """Retorna a conexão com o banco de dados"""
    return pyodbc.connect(connection_string)

@app.route('/')
def index():
    """Página de login"""
    return render_template('index.html')

@app.route('/login', methods=["POST"])
def login():
    """Autenticação do usuário"""
    username = request.form['username']
    password = request.form['password']

    if not username or not password:
        flash('Por favor, insira o nome de usuário e a senha', 'error')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        query = """
            SELECT * 
            FROM dbo.pessoas 
            WHERE username = ? AND password = ?
        """
        cursor = conn.cursor()
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]  # Supondo que o id esteja na primeira coluna
            session['username'] = user[1]  # Supondo que o username esteja na segunda coluna
            return redirect(url_for('home'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Erro ao fazer login: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/home')
def home():
    """Página principal após login"""
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redireciona para login se não estiver logado
    
    try:
        conn = get_db_connection()
        query = "SELECT DISTINCT linha FROM linhas WHERE linha IS NOT NULL"
        df = pd.read_sql(query, conn)
        conn.close()
        
        linhas = df['linha'].tolist()
        return render_template('home.html', linhas=linhas)
    except Exception as e:
        flash(f'Erro ao carregar linhas: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/ver_lpa')
def ver_lpa():
    """Página de consulta de LPAs"""
    if 'user_id' not in session:
        return redirect(url_for('index'))  # Redireciona para login se não estiver logado

    try:
        conn = get_db_connection()
        query = "SELECT DISTINCT linha FROM linhas WHERE linha IS NOT NULL"
        df = pd.read_sql(query, conn)
        conn.close()

        linhas = df['linha'].tolist()
        return render_template('ver_lpa.html', linhas=linhas)
    except Exception as e:
        flash(f'Erro ao carregar linhas: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route("/get_data", methods=["POST"])
def get_data():
    """Carregar as perguntas para a linha de produção selecionada"""
    data = request.json
    production_line = data.get("production_line") 

    if not production_line:
        return jsonify({"error": "Nenhuma linha de produção selecionada."}), 400

    try:
        conn = get_db_connection()
        query = """
            SELECT p.pergunta
            FROM perguntas p
            WHERE p.id IN (
                SELECT lp.pergunta_id
                FROM linha_pergunta lp
                JOIN linhas l ON lp.linha_id = l.id
                WHERE l.linha = ?
            )
        """
        cursor = conn.cursor()
        cursor.execute(query, (production_line,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return jsonify({"error": f"Nenhuma pergunta encontrada para a linha '{production_line}'."}), 404

        perguntas = [{"pergunta": row[0]} for row in rows]
        return jsonify(perguntas)

    except Exception as e:
        return jsonify({"error": f"Erro ao carregar as perguntas: {str(e)}"}), 500


@app.route("/get_user_data")
def get_user_data():
    if "user_id" not in session:
        return jsonify({"error": "Usuário não está logado"}), 401

    try:
        conn = get_db_connection()
        query = """
            SELECT Nr_colaborador, username 
            FROM dbo.pessoas 
            WHERE id = ?
        """
        cursor = conn.cursor()
        cursor.execute(query, (session["user_id"],))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({"error": "Usuário não encontrado"}), 404

        return jsonify({
            "Nr_colaborador": user[0],
            "username": user[1]        
        })

    except Exception as e:
        return jsonify({"error": f"Erro ao carregar dados do usuário: {str(e)}"}), 500
    
@app.route("/save_lpa", methods=["POST"])
def save_lpa():
    if "user_id" not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401

    data = request.json
    linha = data.get("linha")
    respostas = data.get("respostas")  
    turno = data.get("turno")
    registo_peca = data.get("registo_peca")

    if not linha or not respostas or not turno or not registo_peca:
        return jsonify({"error": "Dados incompletos"}), 400

    user_id = session["user_id"]  
    data_auditoria = data.get("data_auditoria")  

    try:
        data_auditoria = datetime.strptime(data_auditoria, "%d/%m/%Y - %H:%M")
    except ValueError:
        return jsonify({"error": "Formato de data inválido. Use o formato DD/MM/YYYY - HH:MM"}), 400

    data_auditoria = data_auditoria.strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        lpa_ids = []  

        for item in respostas:
            pergunta = item["pergunta"]
            resposta = item["resposta"]

            query = """
                SELECT lp.id
                FROM linha_pergunta lp
                JOIN perguntas p ON lp.pergunta_id = p.id
                JOIN linhas l ON lp.linha_id = l.id
                WHERE l.linha = ? AND p.pergunta = ?
            """
            cursor.execute(query, (linha, pergunta))
            linha_pergunta = cursor.fetchone()

            if linha_pergunta:
                linha_pergunta_id = linha_pergunta[0]

                insert_query = """
                    INSERT INTO dbo.LPA (id_pessoa, linha_pergunta_id, resposta, data_auditoria, turno, registo_peca)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(insert_query, (user_id, linha_pergunta_id, resposta, data_auditoria, turno, registo_peca))

        conn.commit()

        for item in respostas:
            if item["resposta"] == "NOK":
                pergunta = item["pergunta"]

                get_lpa_id_query = """
                    SELECT id FROM dbo.LPA 
                    WHERE id_pessoa = ? AND linha_pergunta_id = (
                        SELECT lp.id
                        FROM linha_pergunta lp
                        JOIN perguntas p ON lp.pergunta_id = p.id
                        JOIN linhas l ON lp.linha_id = l.id
                        WHERE l.linha = ? AND p.pergunta = ?
                    )
                    AND data_auditoria = ? AND turno = ? AND registo_peca = ?
                """
                cursor.execute(get_lpa_id_query, (user_id, linha, pergunta, data_auditoria, turno, registo_peca))
                lpa_id = cursor.fetchone()

                if lpa_id:
                    lpa_id = lpa_id[0]  

                    nao_conformidade = item.get("nao_conformidade")
                    acao_corretiva = item.get("acao_corretiva")
                    prazo = item.get("prazo")

                    if not nao_conformidade or not acao_corretiva or not prazo:
                        return jsonify({"error": "Dados de não conformidade incompletos"}), 400

                    insert_incidencia_query = """
                        INSERT INTO dbo.Incidencias (id_LPA, nao_conformidade, acao_corretiva, prazo)
                        VALUES (?, ?, ?, ?)
                    """
                    cursor.execute(insert_incidencia_query, (lpa_id, nao_conformidade, acao_corretiva, prazo))

        conn.commit()
        conn.close()

        return jsonify({"success": "LPA salvo com sucesso!"})

    except Exception as e:
        return jsonify({"error": f"Erro ao salvar LPA: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
    
    