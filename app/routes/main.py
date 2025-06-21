import os
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint,render_template, request, redirect, url_for, flash, session, current_app
from app import db
from app.models.user import User
from app.models.issue import Issue
from app.models.prompt_feedback import PromptFeedback
from sqlalchemy import func
from app.utils.vision_analyzer import VisionAnalyzer
from app.utils.logger import log
from app.config.settings import Settings
from app import app
main_bp = Blueprint('main', __name__)


def calcular_estatisticas():
    """Conecta ao banco e calcula as métricas de ocorrências."""
    with app.app_context():
        # Total de ocorrências reportadas
        ocorrencias_reportadas = Issue.query.count()
        
        # Ocorrências com status 'resolvido'
        # IMPORTANTE: Ajuste a string 'resolvido' se o seu status tiver outro nome
        ocorrencias_resolvidas = Issue.query.filter_by(status='concluida').count()

        # Ocorrências com status 'em_andamento'
        # IMPORTANTE: Ajuste a string 'em_andamento' se o seu status tiver outro nome
        ocorrencias_em_andamento = Issue.query.filter_by(status='pendente').count()
        
        # Impacto Social: número de usuários únicos que reportaram ocorrências
        revisao = Issue.query.filter_by(status='analise').count()

        return {
            "ocorrencias_reportadas": ocorrencias_reportadas,
            "ocorrencias_resolvidas": ocorrencias_resolvidas,
            "ocorrencias_em_andamento": ocorrencias_em_andamento,
            "revisao": revisao
        }

@main_bp.route('/')
def index():
    """Página inicial."""
    return render_template('index.html')


@main_bp.route('/dashboard')
def dashboard():
    """Painel de controle, acessível apenas para usuários logados."""
    user_id = request.cookies.get('id', None)
    if user_id is None:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('auth.login'))
    
    # Obter as estatísticas usando a função existente
    estatisticas = calcular_estatisticas()
    
    # Mapeamento de categorias 
    categorias = {
        1: "Buraco na Via",
        2: "Iluminação Pública",
        3: "Lixo/Entulho",
        4: "Vazamento de Água/Esgoto"
    }
    
    try:
        # Buscar as ocorrências do usuário atual
        issues = Issue.query.filter_by(user_id=request.cookies.get('id', None)).order_by(Issue.created_at.desc()).all()
        
        # Preparar dados para o mapa (serializar)
        issues_json = []
        for issue in issues:
            print(issue.ai_validation_result.get('analysis', ''))
            issues_json.append({
                'issue_code': issue.issue_code,
                'description': issue.description,
                'latitude': float(issue.latitude),
                'longitude': float(issue.longitude),
                'status': issue.status,
                'category_id': issue.category_id,
                'photo_filename': issue.photo_filename,
                'mensagem': issue.ai_validation_result,
            })
        
        log.info(f"Encontradas {len(issues)} ocorrências para o usuário {request.cookies.get('id', None)}")
    except Exception as e:
        log.error(f"Erro ao buscar ocorrências: {str(e)}")
        issues = []
        issues_json = []
        flash("Não foi possível carregar suas ocorrências. Tente novamente mais tarde.", "error")
    
    # Renderizar o template com todos os dados necessários
    return render_template(
        'dashboard.html',
        stats=estatisticas,
        issues=issues,
        issues_json=issues_json,
        categories=categorias
    )

@main_bp.route('/report_issue', methods=['GET', 'POST'])
def report_issue():
    """Página para reportar uma nova ocorrência."""
    user_id = request.cookies.get('id', None)
    if user_id is None:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            # Registrar início do processamento
            log.info(f"Iniciando processamento de nova ocorrência para usuário {request.cookies.get('id', None)}")
            
            # Extrair dados do formulário
            description = request.form.get('description')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            category_id = request.form.get('category_id')
            
            # Validar dados obrigatórios
            if not all([description, latitude, longitude, category_id]):
                log.warning("Formulário incompleto - campos obrigatórios faltando")
                flash('Por favor, preencha todos os campos obrigatórios.', 'error')
                return redirect(url_for('main.report_issue'))
            
            # Gerar código único para a ocorrência
            current_date = datetime.now()
            year_suffix = current_date.strftime('%y')
            month = current_date.strftime('%m')
            prefix = f"CDF-{year_suffix}{month}-"
            
            # Consulta para encontrar o último código deste mês
            last_issue = Issue.query.filter(
                Issue.issue_code.like(f"{prefix}%")
            ).order_by(Issue.issue_code.desc()).first()
            
            if last_issue:
                last_number = int(last_issue.issue_code.split('-')[-1])
                next_number = last_number + 1
            else:
                next_number = 1
            
            # Formatar o código final
            issue_code = f"{prefix}{next_number:04d}"
            log.info(f"Código gerado: {issue_code}")
            
            # Processar upload da foto (se existir)
            photo_filename = None
            photo_path = None
            
            if 'photo' in request.files and request.files['photo'].filename:
                photo = request.files['photo']
                log.info(f"Processando foto: {photo.filename}")
                
                # Garantir que o nome é seguro
                original_filename = secure_filename(photo.filename)
                
                # Criar nome único para o arquivo
                extension = os.path.splitext(original_filename)[1]
                photo_filename = f"{issue_code}{extension}"
                
                # Definir o caminho da pasta de uploads
                upload_folder = os.path.join(current_app.static_folder, 'uploads', 'issues')
                os.makedirs(upload_folder, exist_ok=True)
                
                # Caminho completo do arquivo
                photo_path = os.path.join(upload_folder, photo_filename)
                
                # Salvar o arquivo
                photo.save(photo_path)
                log.info(f"Foto salva em: {photo_path}")
            
            config = Settings()
                
            # efetua a busca do ID da empresa no  config e captura o name, se nao encontrar define como prefeitura
            
            c = next((item["name"] for item in config.COMPANIES if item["id"] == int(category_id)), "RAs")
            
            # Criar nova ocorrência
            new_issue = Issue(
                issue_code=issue_code,
                user_id=request.cookies.get('id', None),
                category_id=category_id,
                description=description,
                latitude=float(latitude),
                longitude=float(longitude),
                photo_filename=photo_filename,
                status='pendente',
                companie=c
            )
            
            # Analisar a imagem se disponível
            if photo_path:
                log.info(f"Iniciando análise de imagem para ocorrência {issue_code}")
                try:
                    # Verificar se a validação por IA está ativada
                    if os.environ.get("ENABLE_AI_VALIDATION", "true").lower() == "true":
                        analyzer = VisionAnalyzer()
                        analysis_result = analyzer.analyze_image(photo_path, int(category_id))
                        
                        human_review= analysis_result.get("human_review", True)
                        if human_review:
                            new_issue.status = 'analise'
                        
                        # Adicionar resultados à ocorrência
                        new_issue.ai_validated = True
                        new_issue.ai_validation_result = analysis_result
                        new_issue.needs_human_review = human_review
                        
                        # Logar o resultado
                        log.info(f"Análise de IA concluída para {issue_code}: {json.dumps(analysis_result)}")
                        
                        # Se precisar de revisão
                        if new_issue.needs_human_review:
                            log.warning(f"Ocorrência {issue_code} marcada para revisão humana")
                    else:
                        log.info("Validação por IA desativada nas configurações")
                except Exception as e:
                    log.error(f"Falha na análise de imagem: {str(e)}")
            
            # Salvar no banco de dados
            db.session.add(new_issue)
            db.session.commit()
            log.info(f"Ocorrência {issue_code} salva com sucesso no banco de dados")

            # Salva informações em json local afim de manter o histórico (orgão competente, usuário, categoria, path imagem)
            history_data = {
                "issue_code": issue_code,
                "user_id": request.cookies.get('id', None),
                "category_id": category_id,
                "photo_filename": photo_filename,
                "companie": c,
                "created_at": current_date.isoformat()
            }
            list_find = [i for i in config.COMPANIES if i["id"] == 0]
            if list_find:
                dict_company = list_find[0]
            else:
                dict_company = {}

            history_dir = os.path.join("app", "integrations")
            os.makedirs(history_dir, exist_ok=True)  # Garante que o diretório existe

            history_filename = os.path.join(
                history_dir, f"{dict_company.get(int(category_id), 'organização')}_history.json"
            )

            # Carrega histórico existente ou cria uma lista vazia
            if os.path.exists(history_filename):
                with open(history_filename, 'r') as history_file:
                    try:
                        history_list = json.load(history_file)
                    except json.JSONDecodeError:
                        history_list = []
            else:
                history_list = []

            # Adiciona o novo dado ao histórico
            history_list.append(history_data)

            # Salva o histórico atualizado
            with open(history_filename, 'w') as history_file:
                json.dump(history_list, history_file, indent=4)
                log.info(f"Histórico salvo em: {history_filename}")

            print("🪲 DEBUG | Dados de histórico salvos:", history_list)

            flash(f'Ocorrência {issue_code} reportada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            log.error(f"Erro ao processar ocorrência: {str(e)}")
            flash(f'Erro ao processar sua solicitação: {str(e)}', 'error')
            return redirect(url_for('main.report_issue'))
    
    return render_template('new_issue.html')

@main_bp.route('/view_issues')
def view_issues():
    """Página para visualizar ocorrências reportadas."""
    user_id = request.cookies.get('id', None)
    if user_id is None:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('auth.login'))

    return render_template('my_reports.html')

# Em app/routes/admin.py (ou onde for adequado)

@main_bp.route('/review_image/<issue_code>', methods=['GET', 'POST'])
def review_image(issue_code):
    """Interface para revisão humana de imagens."""
    issue = Issue.query.filter_by(issue_code=issue_code).first_or_404()
    
    if request.method == 'POST':
        is_valid = request.form.get('is_valid') == 'true'
        feedback_notes = request.form.get('feedback_notes')
        
        # Atualizar a ocorrência
        issue.human_reviewed = True
        issue.human_review_result = is_valid
        
        # Registrar feedback para melhoria dos prompts
        feedback = PromptFeedback(
            issue_id=issue.id,
            category_id=issue.category_id,
            ai_result=issue.ai_validation_result,
            human_result=is_valid,
            feedback_notes=feedback_notes
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        flash('Revisão registrada com sucesso!', 'success')
        return redirect(url_for('admin.review_queue'))
    
    return render_template('admin/review_image.html', issue=issue)


# Adicione estas rotas para servir o manifest e o service worker com os tipos MIME corretos
@app.route('/static/manifest.json')
def serve_manifest():
    return app.send_static_file('manifest.json'), {'Content-Type': 'application/manifest+json'}

@app.route('/static/js/sw.js')
def serve_service_worker():
    return app.send_static_file('js/sw.js'), {'Content-Type': 'application/javascript'}

