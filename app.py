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

     #################### 1º CAMADA #####################################
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
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 7))

        offset = (page - 1) * page_size

        query_linhas = "SELECT id, linha FROM linhas WHERE linha IS NOT NULL ORDER BY linha"
        df_linhas = pd.read_sql(query_linhas, conn)
        todas_linhas = [{"id": row["id"], "linha": row["linha"]} for _, row in df_linhas.iterrows()]

        query_count = """
        SELECT COUNT(DISTINCT l.id) as total
        FROM linhas l
        WHERE l.linha IS NOT NULL
        """
        
        query_paged_lines = """
        SELECT DISTINCT l.id, l.linha
        FROM linhas l
        WHERE l.linha IS NOT NULL
        """

        if filtro_linha:
            query_count += f" AND l.id = {filtro_linha}"
            query_paged_lines += f" AND l.id = {filtro_linha}"

        cursor = conn.cursor()
        cursor.execute(query_count)
        total_lines = cursor.fetchone()[0]
        total_pages = (total_lines + page_size - 1) // page_size 

        query_paged_lines += " ORDER BY l.linha OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        cursor.execute(query_paged_lines, (offset, page_size))
        paged_lines = cursor.fetchall()
        
        current_page_line_ids = [row[0] for row in paged_lines]
        
        if not current_page_line_ids and page > 1:
            return redirect(url_for('home', page=total_pages, page_size=page_size, linha=filtro_linha, turno=turno))
        
        if current_page_line_ids:
            placeholders = ','.join(['?' for _ in current_page_line_ids])
            
            query_lpas = f"""
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
            WHERE l.id IN ({placeholders})
            ORDER BY l.linha
            """
            
            cursor.execute(query_lpas, current_page_line_ids)
            lpas_result = []
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
        else:
            lpas_result = []

        conn.close()

        turnos_para_mostrar = []
        if not turno:
            turnos_para_mostrar = ['Manhã', 'Tarde', 'Noite']
        else:
            turnos_para_mostrar = [turno]

        linhas_com_estado = []
        for linha_id, linha_nome in [(row[0], row[1]) for row in paged_lines]:
            linha_info = {
                "id": linha_id,
                "linha": linha_nome,
                "lpas": []
            }
            
            for t in turnos_para_mostrar:
                lpa_info = next((lpa for lpa in lpas_result if lpa["linha_id"] == linha_id and (lpa["turno"] == t or lpa["turno"] is None)), None)
                
                lpa_obj = {
                    "turno": t,
                    "estado": "Realizado" if lpa_info and lpa_info["resposta"] else "Por Realizar",
                    "auditor": lpa_info["auditor"] if lpa_info and lpa_info["auditor"] else "--",
                    "data_auditoria": lpa_info["data_auditoria"] if lpa_info else None,
                    "resposta": lpa_info["resposta"] if lpa_info else None
                }
                
                linha_info["lpas"].append(lpa_obj)
            
            linhas_com_estado.append(linha_info)

        return render_template('home.html', 
                              linhas=linhas_com_estado,
                              turno=turno,
                              filtro_linha=filtro_linha, 
                              todas_linhas=todas_linhas,
                              page=page,
                              page_size=page_size,
                              total_pages=total_pages)
        
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

    linha_id = request.args.get('linha_id') 
    turno = request.args.get('turno', '') 

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
        turno=turno 
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
            SELECT 
                COALESCE(p1.pergunta, lp_esp.pergunta) AS pergunta, 
                COALESCE(p1.objetivo, lp_esp.objetivo) AS objetivo
            FROM linha_pergunta lp
            JOIN linhas l ON lp.linha_id = l.id
            LEFT JOIN perguntas p1 ON lp.pergunta_id = p1.id
            LEFT JOIN linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
            WHERE l.linha = ?
        """
        cursor = conn.cursor()
        cursor.execute(query, (production_line,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return jsonify({"error": f"Nenhuma pergunta encontrada para a linha '{production_line}'."}), 404

        perguntas = [{"pergunta": row[0], "objetivo": row[1]} for row in rows]
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

        check_query = """
            SELECT COUNT(*)
            FROM dbo.LPA lpa
            JOIN dbo.linha_pergunta lp ON lpa.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            WHERE l.linha = ? 
            AND CONVERT(DATE, lpa.data_auditoria) = CONVERT(DATE, ?) 
            AND lpa.turno = ?
        """
        cursor.execute(check_query, (linha, data_auditoria, turno))
        existing_lpas = cursor.fetchone()[0]

        if existing_lpas > 0:
            return jsonify({"error": f"Já existe um LPA registrado para a linha '{linha}' no turno '{turno}' neste dia."}), 400

        for item in respostas:
            pergunta = item["pergunta"]
            resposta = item["resposta"]

            query = """
                SELECT COALESCE(lp.id, lp_esp.id) AS linha_pergunta_id, 
                       COALESCE(p.objetivo, lp_esp.objetivo) AS objetivo
                FROM linha_pergunta lp
                LEFT JOIN perguntas p ON lp.pergunta_id = p.id
                LEFT JOIN linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
                JOIN linhas l ON lp.linha_id = l.id
                WHERE l.linha = ? AND (p.pergunta = ? OR lp_esp.pergunta = ?)
            """
            cursor.execute(query, (linha, pergunta, pergunta))
            linha_pergunta = cursor.fetchone()

            if linha_pergunta:
                linha_pergunta_id, objetivo = linha_pergunta  

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
        SELECT 
            COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
            lpa.resposta, 
            i.nao_conformidade, 
            i.acao_corretiva, 
            i.prazo
        FROM dbo.LPA lpa
        JOIN dbo.linha_pergunta lp ON lpa.linha_pergunta_id = lp.id
        JOIN dbo.linhas l ON lp.linha_id = l.id
        LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
        LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
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
                COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
                i.nao_conformidade, 
                i.acao_corretiva, 
                i.prazo,
                i.resolvido,
                i.comentario_resolucao
            FROM dbo.Incidencias i
            JOIN dbo.LPA lpa ON i.id_LPA = lpa.id
            JOIN dbo.linha_pergunta lp ON lpa.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
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
                "resolvido": row[9] if row[9] is not None else None, 
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
            if 'id_colaborador' in request.form:
                # Segunda etapa - Verificação final
                id_colaborador = request.form.get('id_colaborador')
                
                cursor.execute("""
                    UPDATE dbo.Incidencias
                    SET resolvido = 'True', 
                        comentario_resolucao = CONCAT(comentario_resolucao, 
                        CHAR(13) + CHAR(10) + CHAR(13) + CHAR(10) + 
                        'Verificado por: ', ?)
                    WHERE id = ?
                """, (id_colaborador, request_id))

                cursor.execute("""
                    UPDATE dbo.LPA
                    SET resposta = 'OK'
                    WHERE id = (SELECT id_LPA FROM dbo.Incidencias WHERE id = ?)
                """, (request_id,))
                
            else:
                # Primeira etapa - Adicionar comentário inicial
                comentario_resolucao = request.form.get('comentario')
                
                cursor.execute("""
                    UPDATE dbo.Incidencias
                    SET resolvido = 'False', comentario_resolucao = ?
                    WHERE id = ?
                """, (comentario_resolucao, request_id))

            conn.commit()
            conn.close()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": True})
            
            return redirect(url_for('incidencias'))

        # GET request - Exibir o formulário
        query = """
            SELECT 
                i.id, 
                l.linha, 
                lpa.data_auditoria, 
                lpa.turno, 
                p.username AS auditor, 
                COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
                i.nao_conformidade, 
                i.acao_corretiva, 
                i.prazo,
                i.resolvido,
                i.comentario_resolucao
            FROM dbo.Incidencias i
            JOIN dbo.LPA lpa ON i.id_LPA = lpa.id
            JOIN dbo.linha_pergunta lp ON lpa.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
            JOIN dbo.pessoas p ON lpa.id_pessoa = p.id
            WHERE i.id = ?
        """

        cursor.execute(query, (request_id,))
        incidencia = cursor.fetchone()
        conn.close()

        if not incidencia:
            flash("Incidência não encontrada!", "danger")
            return redirect(url_for('incidencias'))

        data_formatada = incidencia[2].strftime('%d/%m/%y') if incidencia[2] else None

        incidencia_dict = {
            "id": incidencia[0],
            "linha": incidencia[1],
            "data_auditoria": data_formatada,  
            "turno": incidencia[3],
            "auditor": incidencia[4],
            "pergunta": incidencia[5],
            "nao_conformidade": incidencia[6],
            "acao_corretiva": incidencia[7],
            "prazo": incidencia[8],
            "resolvido": incidencia[9],
            "comentario_resolucao": incidencia[10]
        }

        if incidencia[9] == 'False':  
            return render_template('verificar_incidencia.html', incidencia=incidencia_dict)
        else:
            return render_template('resolver_incidencia.html', incidencia=incidencia_dict)

    except Exception as e:
        flash(f'Erro ao carregar a incidência: {str(e)}', 'error')
        return redirect(url_for('incidencias'))

    #########################  FIM 1º CAMADA #####################################

    #########################  2º CAMADA  #####################################
@app.route('/2_camada', methods=['GET'])
def home2():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()

        turno = request.args.get('turno', '')
        filtro_linha = request.args.get('linha', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 7))

        offset = (page - 1) * page_size

        query_linhas = "SELECT id, linha FROM linhas WHERE linha IS NOT NULL ORDER BY linha"
        df_linhas = pd.read_sql(query_linhas, conn)
        todas_linhas = [{"id": row["id"], "linha": row["linha"]} for _, row in df_linhas.iterrows()]

        query_count = """
        SELECT COUNT(DISTINCT l.id) as total
        FROM linhas l
        WHERE l.linha IS NOT NULL
        """
        
        query_paged_lines = """
        SELECT DISTINCT l.id, l.linha
        FROM linhas l
        WHERE l.linha IS NOT NULL
        """

        if filtro_linha:
            query_count += f" AND l.id = {filtro_linha}"
            query_paged_lines += f" AND l.id = {filtro_linha}"

        cursor = conn.cursor()
        cursor.execute(query_count)
        total_lines = cursor.fetchone()[0]
        total_pages = (total_lines + page_size - 1) // page_size 

        query_paged_lines += " ORDER BY l.linha OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        cursor.execute(query_paged_lines, (offset, page_size))
        paged_lines = cursor.fetchall()
        
        current_page_line_ids = [row[0] for row in paged_lines]
        
        if not current_page_line_ids and page > 1:
            return redirect(url_for('home2', page=total_pages, page_size=page_size, linha=filtro_linha, turno=turno))
        
        if current_page_line_ids:
            placeholders = ','.join(['?' for _ in current_page_line_ids])
            
            query_lpas = f"""
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
            WHERE l.id IN ({placeholders})
            ORDER BY l.linha
            """
            
            cursor.execute(query_lpas, current_page_line_ids)
            lpas_result = []
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
        else:
            lpas_result = []

        conn.close()

        turnos_para_mostrar = []
        if not turno:
            turnos_para_mostrar = ['Manhã', 'Tarde', 'Noite']
        else:
            turnos_para_mostrar = [turno]

        linhas_com_estado = []
        for linha_id, linha_nome in [(row[0], row[1]) for row in paged_lines]:
            linha_info = {
                "id": linha_id,
                "linha": linha_nome,
                "lpas": []
            }
            
            for t in turnos_para_mostrar:
                lpa_info = next((lpa for lpa in lpas_result if lpa["linha_id"] == linha_id and (lpa["turno"] == t or lpa["turno"] is None)), None)
                
                lpa_obj = {
                    "turno": t,
                    "estado": "Realizado" if lpa_info and lpa_info["resposta"] else "Por Realizar",
                    "auditor": lpa_info["auditor"] if lpa_info and lpa_info["auditor"] else "--",
                    "data_auditoria": lpa_info["data_auditoria"] if lpa_info else None,
                    "resposta": lpa_info["resposta"] if lpa_info else None
                }
                
                linha_info["lpas"].append(lpa_obj)
            
            linhas_com_estado.append(linha_info)

        return render_template('2_camada/home2.html', 
                              linhas=linhas_com_estado,
                              turno=turno,
                              filtro_linha=filtro_linha, 
                              todas_linhas=todas_linhas,
                              page=page,
                              page_size=page_size,
                              total_pages=total_pages)
        
    except Exception as e:
        flash(f'Erro ao carregar LPAs: {str(e)}', 'error')
        return redirect(url_for('index'))
    
@app.route('/create_lpa_2_layer')
def create_lpa_2_layer():
    return render_template('2_camada/create_lpa_2_layer.html')



    #########################  FIM 2º CAMADA #####################################
    
    #########################  OTHER CHECKS  #####################################
    
@app.route('/other_checks')
def home3():
    if 'user_id' not in session:
        flash("É necessário fazer login para acessar esta página.", "error")
        return redirect(url_for('index'))  
    return render_template('other_checks/home3.html') 

    #########################  FIM OTHER CHECKS #####################################
    #########################  ANALYTICS #####################################


@app.route('/analytics')
def analytics_dashboard():
    if 'user_id' not in session:
        flash("É necessário fazer login para acessar esta página.", "error")
        return redirect(url_for('index'))  
    return render_template('analytics/dashboard.html') 


@app.route('/api/analytics/dados')
def analytics_dados():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 🟢 LPAs realizados no mês atual (agrupando por conjuntos de 7 perguntas)
        query_lpa = """
            WITH LPAGroups AS (
                SELECT 
                    l.data_auditoria,
                    ln.linha,
                    ln.id as linha_id,
                    COUNT(*) / 7.0 as lpa_count  -- Divide por 7 já que cada LPA tem 7 perguntas
                FROM dbo.LPA l
                JOIN dbo.linhas ln ON l.linha_pergunta_id = ln.id
                WHERE MONTH(l.data_auditoria) = MONTH(GETDATE()) 
                AND YEAR(l.data_auditoria) = YEAR(GETDATE())
                GROUP BY l.data_auditoria, ln.linha, ln.id
            )
            SELECT CAST(SUM(lpa_count) AS INT)
            FROM LPAGroups
        """
        cursor.execute(query_lpa)
        lpa_count = cursor.fetchone()[0] or 0

        # 🟢 Taxa de conformidade (considerando conjuntos de 7 perguntas)
        query_conformidade = """
            WITH LPAResponses AS (
                SELECT 
                    l.data_auditoria,
                    ln.linha,
                    ln.id as linha_id,
                    SUM(CASE WHEN l.resposta = 'OK' THEN 1 ELSE 0 END) as ok_count,
                    COUNT(*) as total_respostas
                FROM dbo.LPA l
                JOIN dbo.linhas ln ON l.linha_pergunta_id = ln.id
                GROUP BY l.data_auditoria, ln.linha, ln.id
            )
            SELECT 
                (SUM(CAST(ok_count AS FLOAT)) * 100.0) / SUM(total_respostas)
            FROM LPAResponses
        """
        cursor.execute(query_conformidade)
        compliance_rate = cursor.fetchone()[0] or 0

        # 🟢 Incidências por categoria
        query_incidencias_categoria = """
            SELECT nao_conformidade, COUNT(*) 
            FROM dbo.Incidencias
            GROUP BY nao_conformidade
        """
        cursor.execute(query_incidencias_categoria)
        incidencias_por_categoria = cursor.fetchall()

        categorias = [row[0] for row in incidencias_por_categoria]
        valores_categoria = [row[1] for row in incidencias_por_categoria]

        # 🟢 LPAs por linha (corrigido para contar conjuntos de 7 perguntas)
        query_lpas_por_linha = """
            WITH LPAGroups AS (
                SELECT 
                    ln.linha,
                    COUNT(*) / 7.0 as lpa_count  -- Divide por 7 para obter o número real de LPAs
                FROM dbo.LPA l
                JOIN dbo.linhas ln ON l.linha_pergunta_id = ln.id
                GROUP BY ln.linha
            )
            SELECT 
                linha,
                CAST(lpa_count AS INT) as lpa_count
            FROM LPAGroups
            ORDER BY linha
        """
        cursor.execute(query_lpas_por_linha)
        lpas_por_linha = cursor.fetchall()

        linhas = [row[0] for row in lpas_por_linha]
        valores_linhas = [row[1] for row in lpas_por_linha]

        conn.close()

        return jsonify({
            "lpasRealizados": lpa_count,
            "taxaConformidade": round(compliance_rate, 2),
            "incidenciasPorCategoria": {"categorias": categorias, "valores": valores_categoria},
            "lpasPorLinha": {"linhas": linhas, "valores": valores_linhas}
        })

    except Exception as e:
        return jsonify({"error": f"Erro ao carregar dados: {str(e)}"}), 500

@app.route('/analytics/incidencias')
def analytics_incidencias():
    return render_template('analytics/analytics_incidencias.html')

@app.route('/analytics/lpa_stats')
def analytics_lpa_stats():
    return render_template('analytics/lpa_stats.html')

@app.route('/analytics/comparativo')
def analytics_comparativo():
    return render_template('analytics/comparativo.html')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
    #########################  FIM ANALYTICS #####################################
