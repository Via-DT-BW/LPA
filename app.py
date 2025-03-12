import json
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import pyodbc
import pandas as pd
from datetime import datetime, timedelta


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

@app.route('/home', methods=['GET'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()

        turno = request.args.get('turno', '')
        filtro_linha = request.args.get('linha', '') 

        query_linhas = "SELECT id, linha FROM linhas WHERE linha IS NOT NULL"
        df_linhas = pd.read_sql(query_linhas, conn)

        query_lpas = """
        SELECT l.id AS linha_id, l.linha, 
               LPA.data_auditoria, LPA.turno, p.username AS auditor, 
               LPA.resposta, LPA.registo_peca
        FROM linhas l
        LEFT JOIN (
            SELECT lp.linha_id, MAX(LPA.data_auditoria) as max_date
            FROM LPA
            JOIN linha_pergunta lp ON LPA.linha_pergunta_id = lp.id
            GROUP BY lp.linha_id
        ) recent ON l.id = recent.linha_id
        LEFT JOIN linha_pergunta lp ON l.id = lp.linha_id
        LEFT JOIN LPA ON lp.id = LPA.linha_pergunta_id AND 
                         (recent.max_date IS NULL OR LPA.data_auditoria = recent.max_date)
        LEFT JOIN pessoas p ON LPA.id_pessoa = p.id
        WHERE l.linha IS NOT NULL
        """

        if turno:
            query_lpas += f" AND LPA.turno = '{turno}'"
        if filtro_linha:
            query_lpas += f" AND l.id = {filtro_linha}"  

        query_lpas += " ORDER BY l.linha"

        lpas_result = []
        cursor = conn.cursor()
        cursor.execute(query_lpas)

        for row in cursor.fetchall():
            lpas_result.append({
                "linha_id": row[0],
                "linha": row[1],
                "data_auditoria": row[2],
                "turno": row[3],
                "auditor": row[4],
                "resposta": row[5],
                "registo_peca": row[6]
            })

        conn.close()

        linhas_com_status = []
        for _, linha_row in df_linhas.iterrows():
            linha_id = linha_row["id"]
            linha_nome = linha_row["linha"]

            lpa_info = next((lpa for lpa in lpas_result if lpa["linha_id"] == linha_id), None)

            if lpa_info:
                linhas_com_status.append({
                    "id": linha_id,
                    "linha": linha_nome,
                    "lpa": lpa_info
                })

        return render_template('home.html', 
                               linhas=linhas_com_status,
                               turno=turno,
                               filtro_linha=filtro_linha, 
                               todas_linhas=df_linhas)  
    except Exception as e:
        flash(f'Erro ao carregar LPAs: {str(e)}', 'error')
        return redirect(url_for('index'))

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
            return redirect(url_for('home'))  
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        flash(f'Erro ao fazer login: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/create_lpa')
def create_lpa():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    linha_id = request.args.get('linha_id')  # Obtém a linha
    turno = request.args.get('turno', '')  # Obtém o turno passado na URL

    conn = get_db_connection()
    query = "SELECT DISTINCT linha FROM linhas WHERE linha IS NOT NULL"
    df = pd.read_sql(query, conn)
    conn.close()

    linhas = df['linha'].tolist()

    linha_selecionada = None
    if linha_id:
        conn = get_db_connection()
        query = "SELECT linha FROM linhas WHERE id = ?"
        linha_df = pd.read_sql(query, conn, params=(linha_id,))
        conn.close()
        
        if not linha_df.empty:
            linha_selecionada = linha_df['linha'].iloc[0]

    return render_template(
        'create_lpa.html',
        linhas=linhas,
        linha_selecionada=linha_selecionada,
        turno=turno  # Passa o turno para o template
    )



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
    data_auditoria = data.get("data_auditoria")  

    if not linha or not respostas or not turno or not registo_peca or not data_auditoria:
        return jsonify({"error": "Dados incompletos"}), 400

    user_id = session["user_id"]  

    try:
        data_auditoria = datetime.strptime(data_auditoria, "%d/%m/%Y - %H:%M") 
    except ValueError:
        return jsonify({"error": "Formato de data inválido. Use o formato DD/MM/YYYY - HH:MM"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        data_inicio = (data_auditoria - timedelta(days=1)).replace(hour=22, minute=0, second=0)  
        data_fim = data_auditoria.replace(hour=23, minute=59, second=59)  

        check_query = """
            SELECT COUNT(*)
            FROM dbo.LPA lpa
            JOIN dbo.linhas l ON lpa.linha_pergunta_id = l.id
            WHERE l.linha = ? 
            AND lpa.data_auditoria BETWEEN ? AND ?
            AND lpa.turno = ?
        """
        cursor.execute(check_query, (linha, data_inicio, data_fim, turno))
        existing_lpas = cursor.fetchone()[0]

        if existing_lpas > 0:
            return jsonify({"error": f"Já existe um LPA registrado para a linha '{linha}' no turno '{turno}' dentro do intervalo permitido."}), 400

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
                cursor.execute(insert_query, (user_id, linha_pergunta_id, resposta, data_auditoria, turno, registo_peca))  # <-- Salva data e hora
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
    

@app.route('/incidencias')
def incidencias():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        turno = request.args.get('turno', '')
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')

        query = """
            SELECT 
                i.id, 
                l.linha, 
                lpa.data_auditoria, 
                lpa.turno, 
                p.username AS auditor, 
                pq.pergunta,
                i.nao_conformidade, 
                i.acao_corretiva, 
                i.prazo,
                i.resolvido,
                i.comentario_resolucao
            FROM dbo.Incidencias i
            JOIN dbo.LPA lpa ON i.id_LPA = lpa.id
            JOIN dbo.linha_pergunta lp ON lpa.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            JOIN dbo.pessoas p ON lpa.id_pessoa = p.id
            WHERE 1=1
        """

        params = []

        if turno:
            query += " AND lpa.turno = ?"
            params.append(turno)

        if data_inicio:
            query += " AND CONVERT(DATE, lpa.data_auditoria) >= CONVERT(DATE, ?)"
            params.append(data_inicio)

        if data_fim:
            query += " AND CONVERT(DATE, lpa.data_auditoria) <= CONVERT(DATE, ?)"
            params.append(data_fim)

        query += " ORDER BY lpa.data_auditoria DESC"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()

        incidencias = []
        for row in results:
            incidencia = {
                "id": row[0],
                "linha": row[1],
                "data_auditoria": row[2],
                "turno": row[3],
                "auditor": row[4],
                "pergunta": row[5],
                "nao_conformidade": row[6],
                "acao_corretiva": row[7],
                "prazo": row[8],
                "resolvido": row[9],
                "comentario_resolucao": row[10]
            }
            incidencias.append(incidencia)

        return render_template('incidencias.html', 
                              incidencias=incidencias, 
                              turno=turno,
                              data_inicio=data_inicio,
                              data_fim=data_fim)

    except Exception as e:
        flash(f'Erro ao carregar incidências: {str(e)}', 'error')
        return redirect(url_for('index'))

    
@app.route('/resolver_incidencia', methods=['GET', 'POST'])
def resolver_incidencia():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        request_id = request.args.get('id', '')

        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            comentario_resolucao = request.form.get('comentario')

            cursor.execute("""
                UPDATE dbo.Incidencias
                SET resolvido = 'True', comentario_resolucao = ?
                WHERE id = ?
            """, (comentario_resolucao, request_id))

            cursor.execute("""
                UPDATE dbo.LPA
                SET resposta = 'OK'
                WHERE id = (SELECT id_LPA FROM dbo.Incidencias WHERE id = ?)
            """, (request_id,))

            conn.commit()
            conn.close()

            flash("Incidência resolvida com sucesso!", "success")
            return redirect(url_for('incidencias'))

        query = """
            SELECT 
                i.id, 
                l.linha, 
                lpa.data_auditoria, 
                lpa.turno, 
                p.username AS auditor, 
                pq.pergunta,
                i.nao_conformidade, 
                i.acao_corretiva, 
                i.prazo
            FROM dbo.Incidencias i
            JOIN dbo.LPA lpa ON i.id_LPA = lpa.id
            JOIN dbo.linha_pergunta lp ON lpa.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            JOIN dbo.pessoas p ON lpa.id_pessoa = p.id
            WHERE i.id = ?
        """

        cursor.execute(query, (request_id,))
        incidencia = cursor.fetchone()
        conn.close()

        if not incidencia:
            flash("Incidência não encontrada!", "danger")
            return redirect(url_for('incidencias'))

        incidencia_dict = {
            "id": incidencia[0],
            "linha": incidencia[1],
            "data_auditoria": incidencia[2],
            "turno": incidencia[3],
            "auditor": incidencia[4],
            "pergunta": incidencia[5],
            "nao_conformidade": incidencia[6],
            "acao_corretiva": incidencia[7],
            "prazo": incidencia[8]
        }

        return render_template('resolver_incidencia.html', incidencia=incidencia_dict)

    except Exception as e:
        flash(f'Erro ao carregar a incidência: {str(e)}', 'error')
        return redirect(url_for('incidencias'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
