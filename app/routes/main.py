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
from app import app
from flask import render_template, session, flash, redirect, url_for, Blueprint
from app.utils.statistics import calcular_estatisticas #, calcular_estatisticas_globais, calcular_estatisticas_usuario # Funções separadas
main_bp = Blueprint('main', __name__)
from functools import wraps
from flask import flash, redirect, url_for

def analista_required(f):
    """
    Decorator que garante que o usuário logado tenha o papel de ANALISTA.
    Se não tiver, redireciona para o dashboard principal com uma mensagem de erro.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Se o usuário não estiver logado ou não for analista
        is_analista = bool(request.cookies.get('is_analista'))
        # Apenas analistas podem acessar esta página.
        if is_analista:
            return f(*args, **kwargs)
        flash("Acesso restrito a usuários com permissão de analista.", "error")
        return redirect(url_for('main.dashboard')) # Ou para a página inicial
    return decorated_function

@main_bp.route('/')
def index():
    """Página inicial."""
    return render_template('index.html')

# Importe o novo decorator
# from app.decorators import analista_required

@main_bp.route('/profile/<int:user_id>')
# @login_required
def view_profile(user_id):
    # 1. Busca o usuário específico pelo ID fornecido na URL
    user_to_check = User.query.get_or_404(user_id)

    # 2. Agora você tem o objeto 'user_to_check' e pode usar a propriedade .is_analista
    #    diretamente nele, sem usar 'current_user'.
    if user_to_check.is_analista:
        role_description = "Este usuário é um Analista."
    else:
        role_description = "Este usuário é um Denunciante."
    
    return render_template(
        'profile.html', 
        user=user_to_check, 
        role_info=role_description
    )

# ROTA 1: O DIRECIONADOR INTELIGENTE
@main_bp.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    """
    Direciona o usuário para o dashboard apropriado com base no seu papel.
    """
    print(">>>> DEBUG | Acessando o dashboard")
    # user_to_view = User.query.get_or_404(user_id)
    is_analista = request.cookies.get('is_analista')
    # Apenas analistas podem acessar esta página.
    print(f">>>> DEBUG | Verificando se é analista: {is_analista}")
    if is_analista == "True":
        flash("Acesso restrito a analistas.", "error")
        return redirect(url_for('main.dashboard_analista'))
    
    return redirect(url_for('main.dashboard_denunciante'))

# ROTA 2: DASHBOARD DO DENUNCIANTE
@main_bp.route('/dashboard/minhas-ocorrencias')
# @login_required
# @analista_required
def dashboard_denunciante():
    """Painel focado no usuário que reporta as ocorrências."""
    
    # # Um denunciante só pode ver suas próprias ocorrências.
    # if not current_user.is_denunciante:
    #     flash("Acesso não autorizado.", "error")
    #     return redirect(url_for('main.dashboard'))

    # Busca apenas as ocorrências DO USUÁRIO ATUAL
    user_issues = Issue.query.filter_by(user_id=request.cookies.get('id')).order_by(Issue.created_at.desc()).all()
    
    # Calcula estatísticas apenas para este usuário
    stats_usuario = {
        "reportadas": len(user_issues),
        "resolvidas": sum(1 for issue in user_issues if issue.status == 'resolvida'),
        "em_andamento": sum(1 for issue in user_issues if issue.status == 'em_andamento')
    }
    
    return render_template('dashboard_denunciante.html', issues=user_issues, stats=stats_usuario)

# ROTA 3: DASHBOARD DO ANALISTA
@main_bp.route('/dashboard/analise')
# @login_required
# @analista_required
def dashboard_analista():
    """Painel de análise de dados para gestores e analistas."""

    

    # Busca TODAS as ocorrências do sistema para análise
    all_issues = Issue.query.order_by(Issue.created_at.desc()).all()
    
    # Calcula estatísticas GLOBAIS
    stats_globais = calcular_estatisticas() # Uma função que busca dados de todo o sistema
    
    # Prepara dados para os mapas interativos e gráficos que criamos anteriormente
    issues_json_para_mapa = [
        {
            'lat': float(issue.latitude), 
            'lon': float(issue.longitude), 
            'categoria': issue.category.name, # Supondo relação
            'status': issue.status
        } for issue in all_issues
    ]
    
    return render_template(
        'dashboard_analista.html', 
        total_issues=len(all_issues), 
        stats=stats_globais,
        map_data=issues_json_para_mapa
    )

@main_bp.route('/report_issue', methods=['GET', 'POST'])
def report_issue():
    """Página para reportar uma nova ocorrência."""
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            # Registrar início do processamento
            log.info(f"Iniciando processamento de nova ocorrência para usuário {session['user_id']}")
            
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
            
            # Criar nova ocorrência
            new_issue = Issue(
                issue_code=issue_code,
                user_id=session['user_id'],
                category_id=category_id,
                description=description,
                latitude=float(latitude),
                longitude=float(longitude),
                photo_filename=photo_filename,
                status='pendente'
            )
            
            # Analisar a imagem se disponível
            if photo_path:
                log.info(f"Iniciando análise de imagem para ocorrência {issue_code}")
                try:
                    # Verificar se a validação por IA está ativada
                    if os.environ.get("ENABLE_AI_VALIDATION", "true").lower() == "true":
                        analyzer = VisionAnalyzer()
                        analysis_result = analyzer.analyze_image(photo_path, int(category_id))
                        
                        # Adicionar resultados à ocorrência
                        new_issue.ai_validated = True
                        new_issue.ai_validation_result = analysis_result
                        new_issue.needs_human_review = analysis_result.get("needs_review", True)
                        
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
    if 'user_id' not in session:
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
