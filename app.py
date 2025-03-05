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

with open(settings_path, "r") as f:
    settings = json.load(f)
connection_string = settings[0]["connection_string_db_teste_jose"]

def get_db_connection():
    return pyodbc.connect(connection_string)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=["POST"])
def login():
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
            session['user_id'] = user[0]  
            session['username'] = user[1]  
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Erro ao fazer login: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('index')) 
    
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

@app.route("/get_data", methods=["POST"])
def get_data():
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
        return jsonify({"error": "Utilizador não autenticado"}), 401

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
                    OUTPUT INSERTED.id
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(insert_query, (user_id, linha_pergunta_id, resposta, data_auditoria, turno, registo_peca))
                lpa_id = cursor.fetchone()[0]  

                if resposta == "NOK":
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

@app.route('/lpa_check')
def lpa_check():
    if 'user_id' not in session:
        return redirect(url_for('index'))  

    try:
        conn = get_db_connection()
        query = "SELECT DISTINCT linha FROM linhas WHERE linha IS NOT NULL"
        df = pd.read_sql(query, conn)
        conn.close()

        linhas = df['linha'].tolist()
        return render_template('lpa_check.html', linhas=linhas)
    except Exception as e:
        flash(f'Erro ao carregar linhas: {str(e)}', 'error')
        return redirect(url_for('index'))
    
@app.route("/get_lpa_data", methods=["POST"])
def get_lpa_data():
    data = request.json
    linha = data.get("linha")

    if not linha:
        return jsonify({"error": "Nenhuma linha de produção selecionada."}), 400

    try:
        conn = get_db_connection()
        query = """
            SELECT lpa.id, l.linha, lpa.data_auditoria, lpa.turno, p.username AS auditor, 
                   lpa.resposta, lp.id AS linha_pergunta_id, pq.pergunta
            FROM dbo.LPA lpa
            JOIN dbo.linha_pergunta lp ON lpa.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            JOIN dbo.pessoas p ON lpa.id_pessoa = p.id
            WHERE l.linha = ?
        """
        cursor = conn.cursor()
        cursor.execute(query, (linha,))
        lpas = cursor.fetchall()
        conn.close()

        lpa_list = []
        for lpa in lpas:
            lpa_list.append({
                "id": lpa[0],
                "linha": lpa[1],
                "data_auditoria": lpa[2].strftime("%Y-%m-%d"),  
                "turno": lpa[3],
                "auditor": lpa[4],
                "resposta": lpa[5],
                "linha_pergunta_id": lpa[6],
                "pergunta": lpa[7],
            })

        return jsonify(lpa_list)

    except Exception as e:
        return jsonify({"error": f"Erro ao buscar LPAs: {str(e)}"}), 500
    
@app.route("/get_lpa_details", methods=["POST"])
def get_lpa_details():
    data = request.json
    linha = data.get("linha")
    data_auditoria = data.get("data_auditoria") 
    turno = data.get("turno")

    if not linha or not data_auditoria or not turno:
        return jsonify({"error": "Dados insuficientes para buscar o LPA."}), 400

    try:
        data_auditoria = datetime.fromisoformat(data_auditoria.split("T")[0])

        conn = get_db_connection()
        query = """
        SELECT pq.pergunta, lpa.resposta, i.nao_conformidade, i.acao_corretiva, i.prazo
        FROM dbo.LPA lpa
        JOIN dbo.linha_pergunta lp ON lpa.linha_pergunta_id = lp.id
        JOIN dbo.linhas l ON lp.linha_id = l.id
        JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
        LEFT JOIN dbo.Incidencias i ON lpa.id = i.id_LPA
        WHERE l.linha = ? 
        AND CONVERT(DATE, lpa.data_auditoria) = CONVERT(DATE, ?) 
        AND lpa.turno = ?
        """

        cursor = conn.cursor()
        cursor.execute(query, (linha, data_auditoria, turno))
        lpas = cursor.fetchall()
        conn.close()

        perguntas = []
        for lpa in lpas:
            pergunta = {
                "pergunta": lpa[0],
                "resposta": lpa[1],
                "incidencias": lpa[2] if lpa[1] == 'NOK' else '',
                "acoes_corretivas": lpa[3] if lpa[1] == 'NOK' else '',
                "prazo": lpa[4] if lpa[1] == 'NOK' else ''
            }
            perguntas.append(pergunta)

        return jsonify(perguntas)

    except Exception as e:
        return jsonify({"error": f"Erro ao buscar detalhes do LPA: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)