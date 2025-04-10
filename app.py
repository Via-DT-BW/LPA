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
    redirect_page = request.form.get('redirect_page', 'index')
    is_lpa_login = request.form.get('is_lpa_login', 'false') == 'true'

    if not username or not password:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Por favor, insira o nome de usuário e a senha.'})
        flash('Por favor, insira o nome de usuário e a senha.', 'error')
        return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT id, name, nr_colaborador, username, role 
            FROM dbo.users 
            WHERE username = ? AND password = ?
        """
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[3]
            session['name'] = user[1]
            session['nr_colaborador'] = user[2]
            session['role'] = user[4].strip() if user[4] else ""

            # For AJAX requests (from "Realizar LPA")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and is_lpa_login:
                return jsonify({
                    'success': True,
                    'role': session['role']
                })

            # For regular form submissions (other menu items)
            role_permissions = {
                "admin": ["home", "home2", "home3", "home4", "analytics_dashboard", "settings_home"],
                "TL": ["home"],
                "PL": ["home2"],
                "PLM": ["home3"],
                "other": ["home4"]
            }
            
            if session['role'] in role_permissions and redirect_page in role_permissions[session['role']]:
                return redirect(url_for(redirect_page))
            else:
                flash("Você não tem permissão para aceder esta página.", "error")
                return redirect(url_for('index'))  # Volta para a página inicial

        # Login failed
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Credenciais inválidas. Tente novamente.'})
        flash('Credenciais inválidas. Tente novamente.', 'error')
        return redirect(url_for('index'))

    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': f'Erro ao fazer login: {str(e)}'})
        flash(f'Erro ao fazer login: {str(e)}', 'error')
        return redirect(url_for('index'))
    
    
     #################### 1º CAMADA #####################################

@app.route('/home', methods=['GET'])
def home():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    user_role = session['role']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        turno = request.args.get('turno', '')
        filtro_linha = request.args.get('linha', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 7))
        offset = (page - 1) * page_size

        # Carrega todas as linhas para o filtro dropdown
        if user_role == 'admin':
            query_linhas = "SELECT DISTINCT id, linha FROM linhas ORDER BY linha"
            cursor.execute(query_linhas)
        else:
            query_linhas = """
                SELECT DISTINCT l.id, l.linha
                FROM linhas l
                JOIN users_linhas lu ON l.id = lu.id_linha
                WHERE lu.id_users = ?
                ORDER BY l.linha
            """
            cursor.execute(query_linhas, (user_id,))
        todas_linhas = [{"id": row[0], "linha": row[1]} for row in cursor.fetchall()]

        # Query base para linhas paginadas
        query_paged_lines = "SELECT DISTINCT linhas.id, linhas.linha FROM linhas"
        filters = []
        params = []

        if user_role != 'admin':
            query_paged_lines += " JOIN users_linhas lu ON linhas.id = lu.id_linha"
            filters.append("lu.id_users = ?")
            params.append(user_id)

        if filtro_linha:
            filters.append("linhas.id = ?")
            params.append(filtro_linha)

        # Adiciona filtros, se houver
        if filters:
            query_paged_lines += " WHERE " + " AND ".join(filters)

        # Query total de linhas
        query_total_lines = query_paged_lines.replace(
            "SELECT DISTINCT linhas.id, linhas.linha",
            "SELECT COUNT(DISTINCT linhas.id)"
        )
        cursor.execute(query_total_lines, params)
        total_lines = cursor.fetchone()[0]
        total_pages = (total_lines + page_size - 1) // page_size

        # Paginação
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size
        query_paged_lines += " ORDER BY linhas.linha OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, page_size])
        cursor.execute(query_paged_lines, params)
        paged_lines = cursor.fetchall()

        current_page_line_ids = [row[0] for row in paged_lines]
        lpas_result = []

        if current_page_line_ids:
            placeholders = ','.join(['?' for _ in current_page_line_ids])
            query_lpas = f"""
                SELECT l.id AS linha_id, l.linha, 
                    LPA.data_auditoria, LPA.turno, 
                    p.name AS auditor, 
                    LPA.resposta, LPA.registo_peca
                FROM linhas l
                LEFT JOIN linha_pergunta lp ON l.id = lp.linha_id
                LEFT JOIN LPA ON lp.id = LPA.linha_pergunta_id
                LEFT JOIN users p ON LPA.id_user = p.id
                WHERE l.id IN ({placeholders})
                ORDER BY l.linha, LPA.turno
            """
            cursor.execute(query_lpas, current_page_line_ids)
            lpas_result = cursor.fetchall()

        conn.close()

        # Mostra todos os turnos se nenhum for selecionado
        turnos_para_mostrar = ['Manhã', 'Tarde', 'Noite'] if not turno else [turno]

        # Monta estrutura para template
        linhas_com_estado = []
        for linha_id, linha_nome in paged_lines:
            linha_info = {"id": linha_id, "linha": linha_nome, "lpas": []}

            for t in turnos_para_mostrar:
                lpa_info = next(
                    (lpa for lpa in lpas_result if lpa[0] == linha_id and lpa[3] == t),
                    None
                )
                lpa_obj = {
                    "turno": t,
                    "estado": "Realizado" if lpa_info else "Por Realizar",
                    "auditor": lpa_info[4] if lpa_info else "--",
                    "data_auditoria": lpa_info[2] if lpa_info else None,
                    "resposta": lpa_info[5] if lpa_info else None
                }
                linha_info["lpas"].append(lpa_obj)

            linhas_com_estado.append(linha_info)

        return render_template(
            'home.html',
            linhas=linhas_com_estado,
            turno=turno,
            filtro_linha=filtro_linha,
            todas_linhas=todas_linhas,
            page=page,
            total_pages=total_pages,
            page_size=page_size
        )

    except Exception as e:
        flash(f'Erro ao carregar LPAs: {str(e)}', 'error')
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
            FROM dbo.users 
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

from flask import request, jsonify, session
from datetime import datetime

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
                    INSERT INTO dbo.LPA (id_user, linha_pergunta_id, resposta, data_auditoria, turno, registo_peca)
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
                        INSERT INTO dbo.Incidencias (id_LPA, nao_conformidade, acao_corretiva, prazo, camada)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_incidencia_query, (lpa_id, nao_conformidade, acao_corretiva, prazo, 1))  

        conn.commit()
        conn.close()

        return jsonify({"success": "LPA guardado com sucesso!"})

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
            JOIN dbo.users p ON lpa.id_user = p.id
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

        # Usamos um dicionário para evitar perguntas duplicadas
        perguntas_dict = {}

        for lpa in lpas:
            pergunta_texto = lpa[0]
            resposta = lpa[1]

            if pergunta_texto not in perguntas_dict:
                perguntas_dict[pergunta_texto] = {
                    "pergunta": pergunta_texto,
                    "resposta": resposta,
                    "incidencias": [],
                    "acoes_corretivas": [],
                    "prazos": []
                }

            # Adicionar informações de incidência apenas se a resposta for "NOK"
            if resposta == 'NOK' and lpa[2]:  # Se houver uma não conformidade
                perguntas_dict[pergunta_texto]["incidencias"].append(lpa[2])
                perguntas_dict[pergunta_texto]["acoes_corretivas"].append(lpa[3])
                perguntas_dict[pergunta_texto]["prazos"].append(lpa[4])

        # Converter dicionário para lista para o JSON
        perguntas = list(perguntas_dict.values())

        return jsonify(perguntas)

    except Exception as e:
        return jsonify({"error": f"Erro ao buscar detalhes do LPA: {str(e)}"}), 500

    

@app.route('/incidencias')
def incidencias():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')

        query = """
        SELECT 
            i.id, 
            l.linha, 
            COALESCE(lpa_3.data_auditoria, lpa_2.data_auditoria, lpa.data_auditoria) AS data_auditoria,
            CASE 
                WHEN i.camada = 3 THEN p3.username
                WHEN i.camada = 2 THEN p2.username
                ELSE p1.username
            END AS auditor, 
            COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
            i.nao_conformidade, 
            i.acao_corretiva, 
            i.prazo,
            i.resolvido,
            i.comentario_resolucao,
            i.camada
        FROM dbo.Incidencias i
        LEFT JOIN dbo.LPA lpa ON i.id_LPA = lpa.id AND i.camada = 1
        LEFT JOIN dbo.LPA_2 lpa_2 ON i.id_LPA = lpa_2.id AND i.camada = 2
        LEFT JOIN dbo.LPA_3 lpa_3 ON i.id_LPA = lpa_3.id AND i.camada = 3
        LEFT JOIN dbo.users p1 ON lpa.id_user = p1.id
        LEFT JOIN dbo.users p2 ON lpa_2.id_user = p2.id
        LEFT JOIN dbo.users p3 ON lpa_3.id_user = p3.id
        LEFT JOIN dbo.linha_pergunta lp ON COALESCE(
            lpa.linha_pergunta_id, 
            lpa_2.linha_pergunta_id, 
            lpa_3.linha_pergunta_id
        ) = lp.id
        LEFT JOIN dbo.linhas l ON lp.linha_id = l.id
        LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
        LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
        WHERE 1=1
        """

        params = []

        if data_inicio:
            query += " AND CONVERT(DATE, COALESCE(lpa.data_auditoria, lpa_2.data_auditoria, lpa_3.data_auditoria)) >= CONVERT(DATE, ?)"
            params.append(data_inicio)

        if data_fim:
            query += " AND CONVERT(DATE, COALESCE(lpa.data_auditoria, lpa_2.data_auditoria, lpa_3.data_auditoria)) <= CONVERT(DATE, ?)"
            params.append(data_fim)

        query += " ORDER BY data_auditoria DESC"

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
                "auditor": row[3],
                "pergunta": row[4],
                "nao_conformidade": row[5],
                "acao_corretiva": row[6],
                "prazo": row[7],
                "resolvido": row[8] if row[8] is not None else None, 
                "comentario_resolucao": row[9],
                "camada": row[10]
            }
            incidencias.append(incidencia)

        return render_template('incidencias/incidencias.html', 
                              incidencias=incidencias, 
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
        
        cursor.execute("SELECT Nr_Colaborador FROM dbo.users WHERE id = ?", (session['user_id'],))
        logged_in_user = cursor.fetchone()
        
        if request.method == 'POST':
            if 'id_colaborador' in request.form:
                id_colaborador = request.form.get('id_colaborador')
                
                if not logged_in_user or str(id_colaborador) != str(logged_in_user[0]):
                    conn.close()
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({"success": False, "error": "Número de colaborador inválido."}), 400
                    else:
                        flash("Número de colaborador inválido.", "danger")
                        return redirect(url_for('incidencias'))
                
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
            JOIN dbo.users p ON lpa.id_user = p.id
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
            return render_template('incidencias/verificar_incidencia.html', incidencia=incidencia_dict)
        else:
            return render_template('incidencias/resolver_incidencia.html', incidencia=incidencia_dict)
    
    except Exception as e:
        flash(f'Erro ao carregar a incidência: {str(e)}', 'error')
        return redirect(url_for('incidencias'))
    #########################  FIM 1º CAMADA #####################################

    #########################  2º CAMADA  #####################################
@app.route('/2_camada', methods=['GET'])
def home2():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    user_role = session['role']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        filtro_linha = request.args.get('linha', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 18))
        offset = (page - 1) * page_size

        # 🔹 Linhas disponíveis para o filtro
        if user_role == 'admin':
            cursor.execute("SELECT DISTINCT id, linha FROM linhas ORDER BY linha")
        else:
            cursor.execute("""
                SELECT DISTINCT l.id, l.linha
                FROM linhas l
                JOIN users_linhas lu ON l.id = lu.id_linha
                WHERE lu.id_users = ?
                ORDER BY l.linha
            """, (user_id,))
        todas_linhas = [{"id": row[0], "linha": row[1]} for row in cursor.fetchall()]

        # 🔹 Construção da query de paginação
        query_paged_lines = "SELECT DISTINCT l.id, l.linha FROM linhas l"
        params = []
        where_clauses = []

        if user_role != 'admin':
            query_paged_lines += " JOIN users_linhas lu ON l.id = lu.id_linha"
            where_clauses.append("lu.id_users = ?")
            params.append(user_id)

        if filtro_linha:
            where_clauses.append("l.id = ?")
            params.append(filtro_linha)

        if where_clauses:
            query_paged_lines += " WHERE " + " AND ".join(where_clauses)

        query_total_lines = query_paged_lines.replace(
            "SELECT DISTINCT l.id, l.linha", "SELECT COUNT(DISTINCT l.id)"
        )

        cursor.execute(query_total_lines, params)
        total_lines = cursor.fetchone()[0]
        total_pages = (total_lines + page_size - 1) // page_size
        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size

        query_paged_lines += " ORDER BY l.linha OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, page_size])
        cursor.execute(query_paged_lines, params)
        paged_lines = cursor.fetchall()

        current_page_line_ids = [row[0] for row in paged_lines]

        # 🔹 Buscar dados da 2ª camada
        if current_page_line_ids:
            placeholders = ','.join(['?' for _ in current_page_line_ids])
            query_lpas_2 = f"""
                SELECT l.id AS linha_id, l.linha, 
                       LPA_2.data_auditoria, p.name AS auditor, 
                       LPA_2.resposta, LPA_2.registo_peca
                FROM linhas l
                LEFT JOIN (
                    SELECT lp.linha_id, MAX(LPA_2.data_auditoria) as max_date
                    FROM LPA_2
                    JOIN linha_pergunta lp ON LPA_2.linha_pergunta_id = lp.id
                    GROUP BY lp.linha_id
                ) recent ON l.id = recent.linha_id
                LEFT JOIN linha_pergunta lp ON l.id = lp.linha_id
                LEFT JOIN LPA_2 ON lp.id = LPA_2.linha_pergunta_id 
                                AND (recent.max_date IS NULL OR LPA_2.data_auditoria = recent.max_date)
                LEFT JOIN users p ON LPA_2.id_user = p.id
                WHERE l.id IN ({placeholders})
                ORDER BY l.linha
            """
            cursor.execute(query_lpas_2, current_page_line_ids)
            lpas_result = [
                {
                    "linha_id": row[0],
                    "linha": row[1],
                    "data_auditoria": row[2],
                    "auditor": row[3],
                    "resposta": row[4],
                    "registo_peca": row[5]
                }
                for row in cursor.fetchall()
            ]
        else:
            lpas_result = []

        conn.close()

        # 🔹 Organizar dados
        linhas_com_estado = []
        for linha_id, linha_nome in paged_lines:
            lpa_info = next((lpa for lpa in lpas_result if lpa["linha_id"] == linha_id), None)
            lpa_obj = {
                "turno": "N/A",
                "estado": "Realizado" if lpa_info and lpa_info["resposta"] else "Por Realizar",
                "auditor": lpa_info["auditor"] if lpa_info and lpa_info["auditor"] else "--",
                "data_auditoria": lpa_info["data_auditoria"] if lpa_info else None,
                "resposta": lpa_info["resposta"] if lpa_info else None
            }

            linhas_com_estado.append({
                "id": linha_id,
                "linha": linha_nome,
                "lpas": [lpa_obj]
            })

        return render_template('2_camada/home2.html', 
                               linhas=linhas_com_estado,
                               filtro_linha=filtro_linha, 
                               todas_linhas=todas_linhas,
                               page=page,
                               total_pages=total_pages,
                               page_size=page_size)

    except Exception as e:
        flash(f'Erro ao carregar LPAs: {str(e)}', 'error')
        return redirect(url_for('index'))



@app.route('/create_lpa2')
def create_lpa2():
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
        '2_camada/create_lpa2.html',
        linhas=linhas,
        linha_selecionada=linha_selecionada,
        turno=turno 
    )


@app.route("/get_data2", methods=["POST"])
def get_data2():
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




@app.route("/get_user_data2")
def get_user_data2():
    if "user_id" not in session:
        return jsonify({"error": "Usuário não está logado"}), 401

    try:
        conn = get_db_connection()
        query = """
            SELECT Nr_colaborador, username 
            FROM dbo.users 
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

@app.route("/save_lpa2", methods=["POST"])
def save_lpa2():
    if "user_id" not in session:
        return jsonify({"error": "Utilizador não autenticado"}), 401

    data = request.json
    linha = data.get("linha")
    respostas = data.get("respostas")
    registo_peca = data.get("registo_peca")
    data_auditoria = data.get("data_auditoria")

    if not linha or not respostas or not registo_peca or not data_auditoria:
        return jsonify({"error": "Dados incompletos"}), 400

    user_id = session["user_id"]

    try:
        data_auditoria = datetime.strptime(data_auditoria, "%d/%m/%Y - %H:%M")
    except ValueError:
        return jsonify({"error": "Formato de data inválido. Use o formato DD/MM/YYYY - HH:MM"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verifica se já existe um LPA 2ª Camada para essa linha e data
        check_query = """
            SELECT COUNT(*)
            FROM dbo.LPA_2 lpa2
            JOIN dbo.linha_pergunta lp ON lpa2.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            WHERE l.linha = ? 
            AND CONVERT(DATE, lpa2.data_auditoria) = CONVERT(DATE, ?)
        """
        cursor.execute(check_query, (linha, data_auditoria))
        existing_lpas = cursor.fetchone()[0]

        if existing_lpas > 0:
            return jsonify({"error": f"Já existe um LPA 2ª Camada registrado para a linha '{linha}' neste dia."}), 400

        for item in respostas:
            pergunta = item.get("pergunta")
            resposta = item.get("resposta")

            query = """
                SELECT COALESCE(lp.id, lp_esp.id) AS linha_pergunta_id,
                       COALESCE(p.objetivo, lp_esp.objetivo) AS objetivo
                FROM dbo.linha_pergunta lp
                LEFT JOIN dbo.perguntas p ON lp.pergunta_id = p.id
                LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
                JOIN dbo.linhas l ON lp.linha_id = l.id
                WHERE l.linha = ? AND (p.pergunta = ? OR lp_esp.pergunta = ?)
            """
            cursor.execute(query, (linha, pergunta, pergunta))
            linha_pergunta = cursor.fetchone()

            if linha_pergunta:
                linha_pergunta_id, objetivo = linha_pergunta

                insert_query = """
                    INSERT INTO dbo.LPA_2 (id_user, linha_pergunta_id, resposta, data_auditoria, registo_peca)
                    OUTPUT INSERTED.id
                    VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(insert_query, (user_id, linha_pergunta_id, resposta, data_auditoria, registo_peca))
                lpa2_id = cursor.fetchone()[0]

                if resposta == "NOK":
                    nao_conformidade = item.get("nao_conformidade")
                    acao_corretiva = item.get("acao_corretiva")
                    prazo = item.get("prazo")

                    if not nao_conformidade or not acao_corretiva or not prazo:
                        return jsonify({"error": "Dados de não conformidade incompletos"}), 400

                    insert_incidencia_query = """
                        INSERT INTO dbo.Incidencias (id_LPA, nao_conformidade, acao_corretiva, prazo, camada)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_incidencia_query, (lpa2_id, nao_conformidade, acao_corretiva, prazo, 2))  # Adiciona camada 2

        conn.commit()
        return jsonify({"success": "LPA 2ª Camada salvo com sucesso!"})

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Erro ao salvar LPA 2ª Camada: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()

    
@app.route("/get_lpa_details2", methods=["POST"])
def get_lpa_details2():
    data = request.json
    linha = data.get("linha")
    data_auditoria = data.get("data_auditoria") 

    if not linha or not data_auditoria:
        return jsonify({"error": "Dados insuficientes para buscar o LPA."}), 400

    try:
        data_auditoria = datetime.fromisoformat(data_auditoria.split("T")[0])

        conn = get_db_connection()
        query = """
        SELECT 
            COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
            lpa_2.resposta, 
            i.nao_conformidade, 
            i.acao_corretiva, 
            i.prazo
        FROM dbo.LPA_2 lpa_2
        JOIN dbo.linha_pergunta lp ON lpa_2.linha_pergunta_id = lp.id
        JOIN dbo.linhas l ON lp.linha_id = l.id
        LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
        LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
        LEFT JOIN dbo.Incidencias i ON lpa_2.id = i.id_LPA
        WHERE l.linha = ? 
        AND CONVERT(DATE, lpa_2.data_auditoria) = CONVERT(DATE, ?)
        """

        cursor = conn.cursor()
        cursor.execute(query, (linha, data_auditoria))
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

            # Verificar se já existe uma pergunta com a mesma descrição
            # Se sim, ignorar a duplicata
            if not any(p["pergunta"] == pergunta["pergunta"] for p in perguntas):
                perguntas.append(pergunta)

        return jsonify(perguntas)

    except Exception as e:
        return jsonify({"error": f"Erro ao buscar detalhes do LPA: {str(e)}"}), 500

    
@app.route('/lpa_check2')
def lpa_check2():
    if 'user_id' not in session:
        return redirect(url_for('index'))  

    try:
        conn = get_db_connection()
        
        query = "SELECT DISTINCT linha FROM linhas WHERE linha IS NOT NULL"
        df = pd.read_sql(query, conn)
        
        conn.close()

        linhas = df['linha'].tolist()
        
        return render_template('2_camada/lpa_check2.html', linhas=linhas)
    
    except Exception as e:
        flash(f'Erro ao carregar linhas: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route("/get_lpa_data2", methods=["POST"])
def get_lpa_data2():
    data = request.json
    linha = data.get("linha")

    if not linha:
        return jsonify({"error": "Nenhuma linha de produção selecionada."}), 400

    try:
        conn = get_db_connection()
        query = """
            SELECT lpa_2.id, l.linha, lpa_2.data_auditoria, p.username AS auditor, 
                   lpa_2.resposta, lp.id AS linha_pergunta_id, pq.pergunta
            FROM dbo.LPA_2 lpa_2
            JOIN dbo.linha_pergunta lp ON lpa_2.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            JOIN dbo.users p ON lpa_2.id_user = p.id
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
                "auditor": lpa[3],
                "resposta": lpa[4],
                "linha_pergunta_id": lpa[5],    
                "pergunta": lpa[6],
            })

        return jsonify(lpa_list)

    except Exception as e:
        return jsonify({"error": f"Erro ao buscar LPAs: {str(e)}"}), 500


    
@app.route('/incidencias2')
def incidencias2():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')

        query = """
               SELECT 
            i.id, 
            l.linha, 
            COALESCE(lpa_2.data_auditoria, lpa.data_auditoria) AS data_auditoria,
            CASE 
                WHEN i.camada = 2 THEN p2.username
                ELSE p1.username 
            END AS auditor, 
            COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
            i.nao_conformidade, 
            i.acao_corretiva, 
            i.prazo,
            i.resolvido,
            i.comentario_resolucao,
            i.camada  -- Adicionando camada para diferenciação
        FROM dbo.Incidencias i
        LEFT JOIN dbo.LPA lpa ON i.id_LPA = lpa.id AND i.camada = 1  -- Apenas para camada 1
        LEFT JOIN dbo.LPA_2 lpa_2 ON i.id_LPA = lpa_2.id AND i.camada = 2  -- Apenas para camada 2
        LEFT JOIN dbo.users p1 ON lpa.id_user = p1.id  -- Auditor da 1ª camada
        LEFT JOIN dbo.users p2 ON lpa_2.id_user = p2.id  -- Auditor da 2ª camada
        JOIN dbo.linha_pergunta lp ON COALESCE(lpa.linha_pergunta_id, lpa_2.linha_pergunta_id) = lp.id
        JOIN dbo.linhas l ON lp.linha_id = l.id
        LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
        LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
        WHERE 1=1  
        """

        params = []

        if data_inicio:
            query += " AND CONVERT(DATE, COALESCE(lpa.data_auditoria, lpa_2.data_auditoria)) >= CONVERT(DATE, ?)"
            params.append(data_inicio)

        if data_fim:
            query += " AND CONVERT(DATE, COALESCE(lpa.data_auditoria, lpa_2.data_auditoria)) <= CONVERT(DATE, ?)"
            params.append(data_fim)

        query += " ORDER BY data_auditoria DESC"

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
                "auditor": row[3],
                "pergunta": row[4],
                "nao_conformidade": row[5],
                "acao_corretiva": row[6],
                "prazo": row[7],
                "resolvido": row[8] if row[8] is not None else None, 
                "comentario_resolucao": row[9]
            }
            incidencias.append(incidencia)

        return render_template('2_camada/incidencias2.html', 
                              incidencias=incidencias, 
                              data_inicio=data_inicio,
                              data_fim=data_fim)

    except Exception as e:
        flash(f'Erro ao carregar incidências: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/resolver_incidencia2', methods=['GET', 'POST'])
def resolver_incidencia2():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        request_id = request.args.get('id', '')
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT Nr_Colaborador FROM dbo.users WHERE id = ?", (session['user_id'],))
        logged_in_user = cursor.fetchone()

        if request.method == 'POST':
            if 'id_colaborador' in request.form:
                id_colaborador = request.form.get('id_colaborador')

                if not logged_in_user or str(id_colaborador) != str(logged_in_user[0]):
                    conn.close()
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({"success": False, "error": "Número de colaborador inválido."}), 400
                    else:
                        flash("Número de colaborador inválido.", "danger")
                        return redirect(url_for('incidencias'))

                cursor.execute("""
                    UPDATE dbo.Incidencias
                    SET resolvido = 'True',
                        comentario_resolucao = CONCAT(comentario_resolucao,
                        CHAR(13) + CHAR(10) + CHAR(13) + CHAR(10) +
                        'Verificado por: ', ?)
                    WHERE id = ?
                """, (id_colaborador, request_id))

                cursor.execute("""
                    UPDATE dbo.LPA_2
                    SET resposta = 'OK'
                    WHERE id = (SELECT id_LPA FROM dbo.Incidencias WHERE id = ?)
                """, (request_id,))
            else:
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
                lpa2.data_auditoria,
                p.username AS auditor,
                COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
                i.nao_conformidade,
                i.acao_corretiva,
                i.prazo,
                i.resolvido,
                i.comentario_resolucao
            FROM dbo.Incidencias i
            JOIN dbo.LPA_2 lpa2 ON i.id_LPA = lpa2.id
            JOIN dbo.linha_pergunta lp ON lpa2.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
            JOIN dbo.users p ON lpa2.id_user = p.id
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
            "auditor": incidencia[3],
            "pergunta": incidencia[4],
            "nao_conformidade": incidencia[5],
            "acao_corretiva": incidencia[6],
            "prazo": incidencia[7],
            "resolvido": incidencia[8],
            "comentario_resolucao": incidencia[9]
        }

        if incidencia[9] == 'False':
            return render_template('2_camada/verificar_incidencia2.html', incidencia=incidencia_dict)
        else:
            return render_template('2_camada/resolver_incidencia2.html', incidencia=incidencia_dict)

    except Exception as e:
        print(f'Erro ao carregar a incidência: {str(e)}', 'error')
        return redirect(url_for('incidencias2'))


    #########################  FIM 2º CAMADA #####################################

    #########################  3º CAMADA  #####################################
    
@app.route('/3_camada', methods=['GET'])
def home3():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    user_role = session['role']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔹 Obter o filtro da linha e a página
        filtro_linha = request.args.get('linha', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 18))
        offset = (page - 1) * page_size

        # 🔹 Obter as linhas para o filtro (Admin vê todas, PL vê as associadas)
        if user_role == 'admin':
            query_linhas = "SELECT DISTINCT id, linha FROM linhas ORDER BY linha"
            cursor.execute(query_linhas)
        else:
            query_linhas = """
                SELECT DISTINCT l.id, l.linha
                FROM linhas l
                JOIN users_linhas lu ON l.id = lu.id_linha
                WHERE lu.id_users = ?
                ORDER BY l.linha
            """
            cursor.execute(query_linhas, (user_id,))

        todas_linhas = [{"id": row[0], "linha": row[1]} for row in cursor.fetchall()]

        query_paged_lines = "SELECT DISTINCT l.id, l.linha FROM linhas l"
        where_clauses = []
        params = []

        if user_role != 'admin':
            query_paged_lines += " JOIN users_linhas lu ON l.id = lu.id_linha"
            where_clauses.append("lu.id_users = ?")
            params.append(user_id)

        if filtro_linha:
            where_clauses.append("l.id = ?")
            params.append(filtro_linha)

        if where_clauses:
            query_paged_lines += " WHERE " + " AND ".join(where_clauses)

        # Total de páginas
        query_total_lines = query_paged_lines.replace(
            "SELECT DISTINCT l.id, l.linha",
            "SELECT COUNT(DISTINCT l.id)"
        )


        cursor.execute(query_total_lines, params)
        total_lines = cursor.fetchone()[0]
        total_pages = (total_lines + page_size - 1) // page_size

        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size

        query_paged_lines += " ORDER BY l.linha OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, page_size])

        cursor.execute(query_paged_lines, params)
        paged_lines = cursor.fetchall()

        current_page_line_ids = [row[0] for row in paged_lines]

        # 🔹 Buscar LPAs da 3ª Camada
        if current_page_line_ids:
            placeholders = ','.join(['?' for _ in current_page_line_ids])
            query_lpas_3 = f"""
            SELECT l.id AS linha_id, l.linha, 
                   LPA_3.data_auditoria, p.name AS auditor, 
                   LPA_3.resposta, LPA_3.registo_peca
            FROM linhas l
            LEFT JOIN (
                SELECT lp.linha_id, MAX(LPA_3.data_auditoria) as max_date
                FROM LPA_3
                JOIN linha_pergunta lp ON LPA_3.linha_pergunta_id = lp.id
                GROUP BY lp.linha_id
            ) recent ON l.id = recent.linha_id
            LEFT JOIN linha_pergunta lp ON l.id = lp.linha_id
            LEFT JOIN LPA_3 ON lp.id = LPA_3.linha_pergunta_id AND 
                             (recent.max_date IS NULL OR LPA_3.data_auditoria = recent.max_date)
            LEFT JOIN users p ON LPA_3.id_user = p.id
            WHERE l.id IN ({placeholders})
            ORDER BY l.linha
            """
            cursor.execute(query_lpas_3, current_page_line_ids)
            lpas_result = [
                {
                    "linha_id": row[0],
                    "linha": row[1],
                    "data_auditoria": row[2],
                    "auditor": row[3],
                    "resposta": row[4],
                    "registo_peca": row[5]
                }
                for row in cursor.fetchall()
            ]
        else:
            lpas_result = []

        conn.close()

        # 🔹 Organizar os dados para o template
        linhas_com_estado = []
        for linha_id, linha_nome in [(row[0], row[1]) for row in paged_lines]:
            linha_info = {
                "id": linha_id,
                "linha": linha_nome,
                "lpas": []
            }

            lpa_info = next((lpa for lpa in lpas_result if lpa["linha_id"] == linha_id), None)

            lpa_obj = {
                "turno": "N/A",
                "estado": "Realizado" if lpa_info and lpa_info["resposta"] else "Por Realizar",
                "auditor": lpa_info["auditor"] if lpa_info and lpa_info["auditor"] else "--",
                "data_auditoria": lpa_info["data_auditoria"] if lpa_info else None,
                "resposta": lpa_info["resposta"] if lpa_info else None
            }

            linha_info["lpas"].append(lpa_obj)
            linhas_com_estado.append(linha_info)

        return render_template('3_camada/home3.html', 
                               linhas=linhas_com_estado,
                               filtro_linha=filtro_linha, 
                               todas_linhas=todas_linhas,
                               page=page,
                               total_pages=total_pages,
                               page_size=page_size)

    except Exception as e:
        flash(f'Erro ao carregar LPAs: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/create_lpa3')
def create_lpa3():
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
        '3_camada/create_lpa3.html',
        linhas=linhas,
        linha_selecionada=linha_selecionada,
        turno=turno 
    )


@app.route("/get_data3", methods=["POST"])
def get_data3():
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




@app.route("/get_user_data3")
def get_user_data3():
    if "user_id" not in session:
        return jsonify({"error": "Usuário não está logado"}), 401

    try:
        conn = get_db_connection()
        query = """
            SELECT Nr_colaborador, username 
            FROM dbo.users 
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

@app.route("/save_lpa3", methods=["POST"])
def save_lpa3():
    if "user_id" not in session:
        return jsonify({"error": "Utilizador não autenticado"}), 401

    data = request.json
    linha = data.get("linha")
    respostas = data.get("respostas")
    registo_peca = data.get("registo_peca")
    data_auditoria = data.get("data_auditoria")

    if not linha or not respostas or not registo_peca or not data_auditoria:
        return jsonify({"error": "Dados incompletos"}), 400

    user_id = session["user_id"]

    try:
        data_auditoria = datetime.strptime(data_auditoria, "%d/%m/%Y - %H:%M")
    except ValueError:
        return jsonify({"error": "Formato de data inválido. Use o formato DD/MM/YYYY - HH:MM"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Verifica se já existe um LPA 3ª Camada para essa linha e data
        check_query = """
            SELECT COUNT(*)
            FROM dbo.LPA_3 lpa3
            JOIN dbo.linha_pergunta lp ON lpa3.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            WHERE l.linha = ? 
            AND CONVERT(DATE, lpa3.data_auditoria) = CONVERT(DATE, ?)
        """
        cursor.execute(check_query, (linha, data_auditoria))
        existing_lpas = cursor.fetchone()[0]

        if existing_lpas > 0:
            return jsonify({"error": f"Já existe um LPA 3ª Camada registado para a linha '{linha}' neste dia."}), 400

        for item in respostas:
            pergunta = item.get("pergunta")
            resposta = item.get("resposta")

            query = """
                SELECT COALESCE(lp.id, lp_esp.id) AS linha_pergunta_id,
                       COALESCE(p.objetivo, lp_esp.objetivo) AS objetivo
                FROM dbo.linha_pergunta lp
                LEFT JOIN dbo.perguntas p ON lp.pergunta_id = p.id
                LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
                JOIN dbo.linhas l ON lp.linha_id = l.id
                WHERE l.linha = ? AND (p.pergunta = ? OR lp_esp.pergunta = ?)
            """
            cursor.execute(query, (linha, pergunta, pergunta))
            linha_pergunta = cursor.fetchone()

            if linha_pergunta:
                linha_pergunta_id, objetivo = linha_pergunta

                insert_query = """
                    INSERT INTO dbo.LPA_3 (id_user, linha_pergunta_id, resposta, data_auditoria, registo_peca)
                    OUTPUT INSERTED.id
                    VALUES (?, ?, ?, ?, ?)
                """
                cursor.execute(insert_query, (user_id, linha_pergunta_id, resposta, data_auditoria, registo_peca))
                lpa2_id = cursor.fetchone()[0]

                if resposta == "NOK":
                    nao_conformidade = item.get("nao_conformidade")
                    acao_corretiva = item.get("acao_corretiva")
                    prazo = item.get("prazo")

                    if not nao_conformidade or not acao_corretiva or not prazo:
                        return jsonify({"error": "Dados de não conformidade incompletos"}), 400

                    insert_incidencia_query = """
                        INSERT INTO dbo.Incidencias (id_LPA, nao_conformidade, acao_corretiva, prazo, camada)
                        VALUES (?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_incidencia_query, (lpa2_id, nao_conformidade, acao_corretiva, prazo, 3)) 

        conn.commit()
        return jsonify({"success": "LPA 3ª Camada guardado com sucesso!"})

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Erro ao guardar LPA 3ª Camada: {str(e)}"}), 500

    finally:
        if conn:
            conn.close()

    
@app.route("/get_lpa_details3", methods=["POST"])
def get_lpa_details3():
    data = request.json
    linha = data.get("linha")
    data_auditoria = data.get("data_auditoria") 

    if not linha or not data_auditoria:
        return jsonify({"error": "Dados insuficientes para buscar o LPA."}), 400

    try:
        data_auditoria = datetime.fromisoformat(data_auditoria.split("T")[0])

        conn = get_db_connection()
        query = """
        SELECT 
            COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
            lpa_3.resposta, 
            i.nao_conformidade, 
            i.acao_corretiva, 
            i.prazo
        FROM dbo.LPA_3 lpa_3
        JOIN dbo.linha_pergunta lp ON lpa_3.linha_pergunta_id = lp.id
        JOIN dbo.linhas l ON lp.linha_id = l.id
        LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
        LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
        LEFT JOIN dbo.Incidencias i ON lpa_3.id = i.id_LPA
        WHERE l.linha = ? 
        AND CONVERT(DATE, lpa_3.data_auditoria) = CONVERT(DATE, ?)
        """

        cursor = conn.cursor()
        cursor.execute(query, (linha, data_auditoria))
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

            # Verificar se já existe uma pergunta com a mesma descrição
            # Se sim, ignorar a duplicata
            if not any(p["pergunta"] == pergunta["pergunta"] for p in perguntas):
                perguntas.append(pergunta)

        return jsonify(perguntas)

    except Exception as e:
        return jsonify({"error": f"Erro ao buscar detalhes do LPA: {str(e)}"}), 500

    
@app.route('/lpa_check3')
def lpa_check3():
    if 'user_id' not in session:
        return redirect(url_for('index'))  

    try:
        conn = get_db_connection()
        
        query = "SELECT DISTINCT linha FROM linhas WHERE linha IS NOT NULL"
        df = pd.read_sql(query, conn)
        
        conn.close()

        linhas = df['linha'].tolist()
        
        return render_template('3_camada/lpa_check3.html', linhas=linhas)
    
    except Exception as e:
        flash(f'Erro ao carregar linhas: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route("/get_lpa_data3", methods=["POST"])
def get_lpa_data3():
    data = request.json
    linha = data.get("linha")

    if not linha:
        return jsonify({"error": "Nenhuma linha de produção selecionada."}), 400

    try:
        conn = get_db_connection()
        query = """
            SELECT lpa_3.id, l.linha, lpa_3.data_auditoria, p.username AS auditor, 
                   lpa_3.resposta, lp.id AS linha_pergunta_id, pq.pergunta
            FROM dbo.LPA_3 lpa_3
            JOIN dbo.linha_pergunta lp ON lpa_3.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            JOIN dbo.users p ON lpa_3.id_user = p.id
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
                "auditor": lpa[3],
                "resposta": lpa[4],
                "linha_pergunta_id": lpa[5],    
                "pergunta": lpa[6],
            })

        return jsonify(lpa_list)

    except Exception as e:
        return jsonify({"error": f"Erro ao buscar LPAs: {str(e)}"}), 500


    
@app.route('/incidencias3')
def incidencias3():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')

        query = """
               SELECT 
            i.id, 
            l.linha, 
            COALESCE(lpa_3.data_auditoria, lpa_2.data_auditoria, lpa.data_auditoria) AS data_auditoria,
            COALESCE(p3.username, p2.username, p1.username) AS auditor,
            COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
            i.nao_conformidade, 
            i.acao_corretiva, 
            i.prazo,
            i.resolvido,
            i.comentario_resolucao,
            i.camada 
        FROM dbo.Incidencias i
        LEFT JOIN dbo.LPA lpa ON i.id_LPA = lpa.id AND i.camada = 1  
        LEFT JOIN dbo.LPA_2 lpa_2 ON i.id_LPA = lpa_2.id AND i.camada = 2  
        LEFT JOIN dbo.LPA_3 lpa_3 ON i.id_LPA = lpa_3.id AND i.camada = 3
        LEFT JOIN dbo.users p1 ON lpa.id_user = p1.id
        LEFT JOIN dbo.users p2 ON lpa_2.id_user = p2.id 
        LEFT JOIN dbo.users p3 ON lpa_3.id_user = p3.id 
        JOIN dbo.linha_pergunta lp ON COALESCE(lpa.linha_pergunta_id, lpa_2.linha_pergunta_id, lpa_3.linha_pergunta_id) = lp.id
        JOIN dbo.linhas l ON lp.linha_id = l.id
        LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
        LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
        WHERE 1=1  
        """

        params = []

        if data_inicio:
            query += " AND CONVERT(DATE, COALESCE(lpa_3.data_auditoria, lpa_2.data_auditoria, lpa.data_auditoria)) >= CONVERT(DATE, ?)"
            params.append(data_inicio)

        if data_fim:
            query += " AND CONVERT(DATE, COALESCE(lpa_3.data_auditoria, lpa_2.data_auditoria, lpa.data_auditoria)) <= CONVERT(DATE, ?)"
            params.append(data_fim)


        query += " ORDER BY data_auditoria DESC"

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
                "auditor": row[3],
                "pergunta": row[4],
                "nao_conformidade": row[5],
                "acao_corretiva": row[6],
                "prazo": row[7],
                "resolvido": row[8] if row[8] is not None else None, 
                "comentario_resolucao": row[9]
            }
            incidencias.append(incidencia)

        return render_template('3_camada/incidencias3.html', 
                              incidencias=incidencias, 
                              data_inicio=data_inicio,
                              data_fim=data_fim)

    except Exception as e:
        print(f'Erro ao carregar incidências: {str(e)}', 'error')
        return redirect(url_for('index'))
    
@app.route('/resolver_incidencia3', methods=['GET', 'POST'])
def resolver_incidencia3():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    try:
        request_id = request.args.get('id', '')
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT Nr_Colaborador FROM dbo.users WHERE id = ?", (session['user_id'],))
        logged_in_user = cursor.fetchone()

        if request.method == 'POST':
            if 'id_colaborador' in request.form:
                id_colaborador = request.form.get('id_colaborador')

                if not logged_in_user or str(id_colaborador) != str(logged_in_user[0]):
                    conn.close()
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({"success": False, "error": "Número de colaborador inválido."}), 400
                    else:
                        flash("Número de colaborador inválido.", "danger")
                        return redirect(url_for('incidencias'))

                cursor.execute("""
                    UPDATE dbo.Incidencias
                    SET resolvido = 'True',
                        comentario_resolucao = CONCAT(comentario_resolucao,
                        CHAR(13) + CHAR(10) + CHAR(13) + CHAR(10) +
                        'Verificado por: ', ?)
                    WHERE id = ?
                """, (id_colaborador, request_id))

                cursor.execute("""
                    UPDATE dbo.LPA_3
                    SET resposta = 'OK'
                    WHERE id = (SELECT id_LPA FROM dbo.Incidencias WHERE id = ?)
                """, (request_id,))
            else:
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
                lpa3.data_auditoria,
                p.username AS auditor,
                COALESCE(pq.pergunta, lp_esp.pergunta) AS pergunta,
                i.nao_conformidade,
                i.acao_corretiva,
                i.prazo,
                i.resolvido,
                i.comentario_resolucao
            FROM dbo.Incidencias i
            JOIN dbo.LPA_3 lpa3 ON i.id_LPA = lpa3.id
            JOIN dbo.linha_pergunta lp ON lpa3.linha_pergunta_id = lp.id
            JOIN dbo.linhas l ON lp.linha_id = l.id
            LEFT JOIN dbo.perguntas pq ON lp.pergunta_id = pq.id
            LEFT JOIN dbo.linha_pergunta_especifica lp_esp ON lp.linha_pergunta_especifica_id = lp_esp.id
            JOIN dbo.users p ON lpa3.id_user = p.id
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
            "auditor": incidencia[3],
            "pergunta": incidencia[4],
            "nao_conformidade": incidencia[5],
            "acao_corretiva": incidencia[6],
            "prazo": incidencia[7],
            "resolvido": incidencia[8],
            "comentario_resolucao": incidencia[9]
        }

        if incidencia[9] == 'False':
            return render_template('3_camada/verificar_incidencia2.html', incidencia=incidencia_dict)
        else:
            return render_template('3_camada/resolver_incidencia2.html', incidencia=incidencia_dict)

    except Exception as e:
        print(f'Erro ao carregar a incidência: {str(e)}', 'error')
        return redirect(url_for('incidencias3'))




    #########################  FIM 3º CAMADA  #####################################
    
    #########################  OTHER CHECKS  #####################################
    
@app.route('/other_checks', methods=['GET'])
def home4():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    user_id = session['user_id']
    user_role = session['role']

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔹 Obter o filtro da linha e a página
        filtro_linha = request.args.get('linha', '')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 18))
        offset = (page - 1) * page_size

        # 🔹 Obter as linhas para o filtro (Admin vê todas, PL vê as associadas)
        if user_role == 'admin':
            query_linhas = "SELECT DISTINCT id, linha FROM linhas ORDER BY linha"
            cursor.execute(query_linhas)
        else:
            query_linhas = """
                SELECT DISTINCT l.id, l.linha
                FROM linhas l
                JOIN users_linhas lu ON l.id = lu.id_linha
                WHERE lu.id_users = ?
                ORDER BY l.linha
            """
            cursor.execute(query_linhas, (user_id,))

        todas_linhas = [{"id": row[0], "linha": row[1]} for row in cursor.fetchall()]

        # 🔹 Obter linhas paginadas
        query_paged_lines = """
        SELECT DISTINCT l.id, l.linha
        FROM linhas l
        """
        params = []

        if user_role != 'admin':
            query_paged_lines += """
                JOIN users_linhas lu ON l.id = lu.id_linha
                WHERE lu.id_users = ?
            """
            params.append(user_id)

        if filtro_linha:
            query_paged_lines += " AND l.id = ?"
            params.append(filtro_linha)

        query_total_lines = query_paged_lines.replace(
            "SELECT DISTINCT l.id, l.linha",
            "SELECT COUNT(DISTINCT l.id)"
        )

        cursor.execute(query_total_lines, params)
        total_lines = cursor.fetchone()[0]
        total_pages = (total_lines + page_size - 1) // page_size

        page = max(1, min(page, total_pages))
        offset = (page - 1) * page_size

        query_paged_lines += " ORDER BY l.linha OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, page_size])

        cursor.execute(query_paged_lines, params)
        paged_lines = cursor.fetchall()

        current_page_line_ids = [row[0] for row in paged_lines]

        # 🔹 Buscar LPAs da 3ª Camada
        if current_page_line_ids:
            placeholders = ','.join(['?' for _ in current_page_line_ids])
            query_lpas_3 = f"""
            SELECT l.id AS linha_id, l.linha, 
                   LPA_3.data_auditoria, p.username AS auditor, 
                   LPA_3.resposta, LPA_3.registo_peca
            FROM linhas l
            LEFT JOIN (
                SELECT lp.linha_id, MAX(LPA_3.data_auditoria) as max_date
                FROM LPA_3
                JOIN linha_pergunta lp ON LPA_3.linha_pergunta_id = lp.id
                GROUP BY lp.linha_id
            ) recent ON l.id = recent.linha_id
            LEFT JOIN linha_pergunta lp ON l.id = lp.linha_id
            LEFT JOIN LPA_3 ON lp.id = LPA_3.linha_pergunta_id AND 
                             (recent.max_date IS NULL OR LPA_3.data_auditoria = recent.max_date)
            LEFT JOIN users p ON LPA_3.id_user = p.id
            WHERE l.id IN ({placeholders})
            ORDER BY l.linha
            """
            cursor.execute(query_lpas_3, current_page_line_ids)
            lpas_result = [
                {
                    "linha_id": row[0],
                    "linha": row[1],
                    "data_auditoria": row[2],
                    "auditor": row[3],
                    "resposta": row[4],
                    "registo_peca": row[5]
                }
                for row in cursor.fetchall()
            ]
        else:
            lpas_result = []

        conn.close()

        # 🔹 Organizar os dados para o template
        linhas_com_estado = []
        for linha_id, linha_nome in [(row[0], row[1]) for row in paged_lines]:
            linha_info = {
                "id": linha_id,
                "linha": linha_nome,
                "lpas": []
            }

            lpa_info = next((lpa for lpa in lpas_result if lpa["linha_id"] == linha_id), None)

            lpa_obj = {
                "turno": "N/A",
                "estado": "Realizado" if lpa_info and lpa_info["resposta"] else "Por Realizar",
                "auditor": lpa_info["auditor"] if lpa_info and lpa_info["auditor"] else "--",
                "data_auditoria": lpa_info["data_auditoria"] if lpa_info else None,
                "resposta": lpa_info["resposta"] if lpa_info else None
            }

            linha_info["lpas"].append(lpa_obj)
            linhas_com_estado.append(linha_info)

        return render_template('other_checks/home4.html', 
                               linhas=linhas_com_estado,
                               filtro_linha=filtro_linha, 
                               todas_linhas=todas_linhas,
                               page=page,
                               total_pages=total_pages,
                               page_size=page_size)

    except Exception as e:
        flash(f'Erro ao carregar LPAs: {str(e)}', 'error')
        return redirect(url_for('index'))

    #########################  FIM OTHER CHECKS #####################################
    #########################  ANALYTICS #####################################


@app.route('/analytics')
def analytics_dashboard():
    if 'user_id' not in session:
        flash("É necessário fazer login para acessar esta página.", "error")
        return redirect(url_for('index'))  
    return render_template('analytics/dashboard.html', request=request)

@app.route('/api/analytics/dados')
def analytics_dados():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401  # Retorna erro se não estiver autenticado
    
    periodo = request.args.get('periodo', 'mes')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Define as condições de data apenas para a tabela LPA
        data_condition = ""
        if periodo == 'semana':
            data_condition = "AND DATEDIFF(day, data_auditoria, GETDATE()) <= 7"
        elif periodo == 'mes':
            data_condition = "AND MONTH(data_auditoria) = MONTH(GETDATE()) AND YEAR(data_auditoria) = YEAR(GETDATE())"
        elif periodo == 'trimestre':
            data_condition = "AND DATEDIFF(day, data_auditoria, GETDATE()) <= 90"
        
      # Contagem correta de LPAs realizados (únicos por data e turno)
        query_lpa_count = f"""
            SELECT COUNT(DISTINCT CONCAT(data_auditoria, turno)) 
            FROM dbo.LPA
            WHERE 1=1 {data_condition}
        """
        cursor.execute(query_lpa_count)
        total_lpas = cursor.fetchone()[0] or 0


        
        # Contagem de LPAs "OK"
        query_ok_count = f"""
            SELECT COUNT(*) 
            FROM dbo.LPA
            WHERE resposta = 'OK' {data_condition}
        """
        cursor.execute(query_ok_count)
        ok_count = cursor.fetchone()[0] or 0
        
        # Contagem de LPAs "NOK"
        query_nok_count = f"""
            SELECT COUNT(*) 
            FROM dbo.LPA
            WHERE resposta = 'NOK' {data_condition}
        """
        cursor.execute(query_nok_count)
        nok_count = cursor.fetchone()[0] or 0
        
        query_incidencias_abertas = """
            SELECT COUNT(*) FROM dbo.Incidencias WHERE resolvido IS NULL
        """
        cursor.execute(query_incidencias_abertas)
        incidencias_abertas = cursor.fetchone()[0] or 0

        query_incidencias_pendentes = """
            SELECT COUNT(*) FROM dbo.Incidencias WHERE LOWER(resolvido) = 'false'
        """
        cursor.execute(query_incidencias_pendentes)
        incidencias_pendentes = cursor.fetchone()[0] or 0

        query_incidencias_resolvidas = """
            SELECT COUNT(*) FROM dbo.Incidencias WHERE LOWER(resolvido) = 'true'
        """
        cursor.execute(query_incidencias_resolvidas)
        incidencias_resolvidas = cursor.fetchone()[0] or 0


        # Preparar dados para o gráfico
        categorias = ['OK', 'NOK', 'Total LPAs', 'Incidências Abertas', 'Incidências Pendentes', 'Incidências Resolvidas']
        valores = [ok_count, nok_count, total_lpas, incidencias_abertas, incidencias_pendentes, incidencias_resolvidas]
        
        conn.close()
        
        # Retorna os dados como JSON para o frontend
        return jsonify({
            "totalLPAs": total_lpas,
            "okCount": ok_count,
            "nokCount": nok_count,
            "incidenciasAbertas": incidencias_abertas,
            "incidenciasPendentes": incidencias_pendentes,
            "incidenciasResolvidas": incidencias_resolvidas,
            "categorias": categorias,
            "valores": valores
        })
    
    except Exception as e:
        return jsonify({"error": f"Erro ao carregar dados: {str(e)}"}), 500

@app.route('/analytics/incidencias')
def analytics_incidencias():
    if 'user_id' not in session:
        flash("É necessário fazer login para acessar esta página.", "error")
        return redirect(url_for('index'))
    return render_template('analytics/analytics_incidencias.html')

@app.route('/api/analytics/incidencias')
def api_analytics_incidencias():
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Query para buscar as incidências e unir com a tabela LPA
        query_base = """
        SELECT 
            i.id, 
            i.id_LPA,
            ISNULL(i.nao_conformidade, '') AS nao_conformidade, 
            ISNULL(i.acao_corretiva, 'Não definida') AS acao_corretiva, 
            ISNULL(i.prazo, '') AS prazo,
            ISNULL(i.resolvido, 'False') AS resolvido,
            ISNULL(i.comentario_resolucao, 'Nenhum') AS comentario_resolucao,
            l.data_auditoria
        FROM dbo.Incidencias i
        JOIN dbo.LPA l ON i.id_LPA = l.id
        """

        cursor.execute(query_base)
        incidencias = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

        # Estatísticas
        total_incidencias = len(incidencias)
        incidencias_pendentes = sum(1 for inc in incidencias if inc['resolvido'].lower() != 'true')
        incidencias_resolvidas = total_incidencias - incidencias_pendentes

        # Tendência de incidências por data de auditoria
        tendencia_incidencias = {}
        for inc in incidencias:
            data = str(inc['data_auditoria'].date()) if inc['data_auditoria'] else "Sem data"
            tendencia_incidencias[data] = tendencia_incidencias.get(data, 0) + 1

        conn.close()

        return jsonify({
            "incidencias": incidencias,
            "total_incidencias": total_incidencias,
            "incidencias_pendentes": incidencias_pendentes,
            "incidencias_resolvidas": incidencias_resolvidas,
            "tendencia_incidencias": {
                "datas": list(tendencia_incidencias.keys()),
                "quantidades": list(tendencia_incidencias.values())
            }
        })

    except Exception as e:
        return jsonify({"error": f"Erro ao carregar dados: {str(e)}"}), 500


@app.route('/api/incidencia/<int:id>')
def get_incidencia_detalhes(id):
    if 'user_id' not in session:
        return jsonify({"error": "Usuário não autenticado"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                i.id, 
                i.id_LPA,
                i.nao_conformidade, 
                i.acao_corretiva, 
                i.prazo,
                i.resolvido,
                i.comentario_resolucao,
                l.data_auditoria
            FROM dbo.Incidencias i
            JOIN dbo.LPA l ON i.id_LPA = l.id
            WHERE i.id = ?
        """, (id,))

        incidencia = cursor.fetchone()
        conn.close()

        if not incidencia:
            return jsonify({"error": "Incidência não encontrada"}), 404

        return jsonify(dict(zip([
            'id', 'id_LPA', 'nao_conformidade', 
            'acao_corretiva', 'prazo', 'resolvido', 
            'comentario_resolucao', 'data_auditoria'
        ], incidencia)))

    except Exception as e:
        return jsonify({"error": f"Erro ao carregar detalhes: {str(e)}"}), 500


@app.route('/analytics/lpa_stats')
def analytics_lpa_stats():
    return render_template('analytics/lpa_stats.html')

@app.route('/analytics/comparativo')
def analytics_comparativo():
    return render_template('analytics/comparativo.html')
  #########################  FIM ANALYTICS #####################################
    
    #########################  SETTINGS #####################################
@app.route('/settings')
def settings_home():
    return render_template('settings/settings_home.html')

@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Execute a consulta SQL para obter todos os usuários
        cursor.execute("""
            SELECT [id], [name], [nr_colaborador], [username], [phone], [email], [role]
            FROM [teste_jose].[dbo].[users]
        """)
        
        # Converter resultado em lista de dicionários
        columns = [column[0] for column in cursor.description]
        users = []
        for row in cursor.fetchall():
            users.append(dict(zip(columns, row)))
        
        conn.close()
        return jsonify(users)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT [id], [name], [nr_colaborador], [username], [phone], [email], [role]
            FROM [teste_jose].[dbo].[users]
            WHERE [id] = ?
        """, user_id)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [column[0] for column in cursor.description]
            user = dict(zip(columns, row))
            return jsonify(user)
        else:
            return jsonify({"error": "Utilizador não encontrado"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users', methods=['POST'])
def add_user():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""select max(id) from [teste_jose].[dbo].[users] """)
        max_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO [teste_jose].[dbo].[users]
            ([id],[name], [nr_colaborador], [username], [phone], [email], [password], [role])
            VALUES (?,?, ?, ?, ?, ?, ?, ?)
        """, 
        max_id + 1,
        data['name'], 
        data['nr_colaborador'] if data['nr_colaborador'] else None, 
        data['username'], 
        data['phone'], 
        data['email'], 
        data['password'], 
        data['role'])
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Utilizador adicionado com sucesso"}), 201
    
    except Exception as e:
        print(f"Erro ao adicionar utilizador: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se o campo password foi fornecido
        if 'password' in data and data['password']:
            cursor.execute("""
                UPDATE [teste_jose].[dbo].[users]
                SET [name] = ?, [nr_colaborador] = ?, [username] = ?, 
                    [phone] = ?, [email] = ?, [password] = ?, [role] = ?
                WHERE [id] = ?
            """, 
            data['name'], 
            data['nr_colaborador'] if data['nr_colaborador'] else None, 
            data['username'], 
            data['phone'], 
            data['email'], 
            data['password'], 
            data['role'],
            user_id)
        else:
            cursor.execute("""
                UPDATE [teste_jose].[dbo].[users]
                SET [name] = ?, [nr_colaborador] = ?, [username] = ?, 
                    [phone] = ?, [email] = ?, [role] = ?
                WHERE [id] = ?
            """, 
            data['name'], 
            data['nr_colaborador'] if data['nr_colaborador'] else None, 
            data['username'], 
            data['phone'], 
            data['email'], 
            data['role'],
            user_id)
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Utilizador atualizado com sucesso"})
    
    except Exception as e:
        print(f"Erro ao atualizar utilizador: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>/role', methods=['PUT'])
def update_user_role(user_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE [teste_jose].[dbo].[users]
            SET [role] = ?
            WHERE [id] = ?
        """, data['role'], user_id)
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Role atualizado com sucesso"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM [teste_jose].[dbo].[users]
            WHERE [id] = ?
        """, user_id)
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Utilizador eliminado com sucesso"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/perguntas_linhas')
def perguntas_linhas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obter todas as linhas para o filtro
        cursor.execute("""
            SELECT [id], [linha]
            FROM [teste_jose].[dbo].[linhas]
            ORDER BY [linha]
        """)
        todas_linhas = []
        for row in cursor.fetchall():
            todas_linhas.append({"id": row[0], "linha": row[1]})

        # Processar parâmetros de filtro
        filtro_linha = request.args.get('linha', '')
        page = int(request.args.get('page', 1))
        items_per_page = 15  # Aumentado para 20 itens por página

        # Construir a consulta base
        query_base = """
            SELECT lpe.[id], lpe.[pergunta], l.[linha], lpe.[linha_id], lpe.[objetivo]
            FROM [teste_jose].[dbo].[linha_pergunta_especifica] lpe
            JOIN [teste_jose].[dbo].[linhas] l ON lpe.[linha_id] = l.[id]
        """

        # Adicionar filtro se necessário
        params = []
        if filtro_linha:
            query_base += " WHERE lpe.[linha_id] = ?"
            params.append(filtro_linha)

        # Consulta para contagem total
        cursor.execute(f"SELECT COUNT(*) FROM ({query_base}) as count_query", params)
        total_items = cursor.fetchone()[0]
        total_pages = (total_items + items_per_page - 1) // items_per_page

        # Consulta final com paginação
        offset = (page - 1) * items_per_page
        query_final = f"{query_base} ORDER BY l.[linha], lpe.[id] OFFSET ? ROWS FETCH NEXT ? ROWS ONLY"
        params.extend([offset, items_per_page])
        
        cursor.execute(query_final, params)
        
        perguntas = []
        for row in cursor.fetchall():
            perguntas.append({
                "id": row[0],
                "pergunta": row[1],
                "linha": row[2],
                "linha_id": row[3],
                "objetivo": row[4] if row[4] else ""
            })
        
        conn.close()

        return render_template(
            'settings/perguntas_linhas.html',
            perguntas=perguntas,
            todas_linhas=todas_linhas,
            filtro_linha=filtro_linha,
            page=page,
            total_pages=total_pages
        )
    
    except Exception as e:
        print(f"Erro ao carregar perguntas por linha: {str(e)}")
        return render_template('error.html', error=str(e))

# API para obter uma pergunta específica
@app.route('/api/perguntas/<int:pergunta_id>', methods=['GET'])
def get_pergunta(pergunta_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT lpe.[id], lpe.[linha_id], l.[linha], lpe.[pergunta], lpe.[objetivo]
            FROM [teste_jose].[dbo].[linha_pergunta_especifica] lpe
            JOIN [teste_jose].[dbo].[linhas] l ON lpe.[linha_id] = l.[id]
            WHERE lpe.[id] = ?
        """, pergunta_id)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            pergunta = {
                "id": row[0],
                "linha_id": row[1],
                "linha": row[2],
                "pergunta": row[3],
                "objetivo": row[4] if row[4] else ""
            }
            return jsonify(pergunta)
        else:
            return jsonify({"error": "Pergunta não encontrada"}), 404
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API para atualizar uma pergunta
@app.route('/api/perguntas/<int:pergunta_id>', methods=['PUT'])
def update_pergunta(pergunta_id):
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE [teste_jose].[dbo].[linha_pergunta_especifica]
            SET [linha_id] = ?, [pergunta] = ?, [objetivo] = ?
            WHERE [id] = ?
        """, 
        data['linha_id'], 
        data['pergunta'], 
        data['objetivo'],
        pergunta_id)
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Pergunta atualizada com sucesso"})
    
    except Exception as e:
        print(f"Erro ao atualizar pergunta: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API para adicionar uma nova pergunta
@app.route('/api/perguntas', methods=['POST'])
def add_pergunta():
    try:
        data = request.json
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obter o próximo ID disponível
        cursor.execute("""SELECT MAX(id) FROM [teste_jose].[dbo].[linha_pergunta_especifica]""")
        max_id = cursor.fetchone()[0]
        next_id = 1 if max_id is None else max_id + 1
        
        cursor.execute("""
            INSERT INTO [teste_jose].[dbo].[linha_pergunta_especifica]
            ([id], [pergunta], [linha], [linha_id], [objetivo])
            VALUES (?, ?, ?, ?, ?)
        """, 
        next_id,
        data['pergunta'],
        data['linha'],  # Nome da linha
        data['linha_id'],  # ID da linha
        data['objetivo'])
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Pergunta adicionada com sucesso", "id": next_id}), 201
    
    except Exception as e:
        print(f"Erro ao adicionar pergunta: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API para excluir uma pergunta
@app.route('/api/perguntas/<int:pergunta_id>', methods=['DELETE'])
def delete_pergunta(pergunta_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM [teste_jose].[dbo].[linha_pergunta_especifica]
            WHERE [id] = ?
        """, pergunta_id)
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Pergunta excluída com sucesso"})
    
    except Exception as e:
        print(f"Erro ao excluir pergunta: {str(e)}")
        return jsonify({"error": str(e)}), 500

  #########################  FIM SETTINGS #####################################



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
  
    





