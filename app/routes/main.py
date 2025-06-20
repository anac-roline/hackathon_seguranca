import os
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint,render_template, request, redirect, url_for, flash, session, current_app
from app import db
from app.models.issue import Issue
from sqlalchemy import func

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Página inicial."""
    return render_template('index.html')


@main_bp.route('/dashboard')
def dashboard():
    """Painel de controle, acessível apenas para usuários logados."""
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('auth.login'))

    return render_template('dashboard.html')

@main_bp.route('/report_issue', methods=['GET', 'POST'])
def report_issue():
    """Página para reportar uma nova ocorrência."""
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        try:
            # Extrair dados do formulário
            # title = request.form.get('title')
            description = request.form.get('description')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            category_id = request.form.get('category_id')
            
            # Validar dados obrigatórios
            if not all([description, latitude, longitude, category_id]):
                flash('Por favor, preencha todos os campos obrigatórios.', 'error')
                return redirect(url_for('main.report_issue'))
            
            # Gerar código único para a ocorrência (CDF-AAMM-NNNN)
            current_date = datetime.now()
            year_suffix = current_date.strftime('%y')  # Ano com 2 dígitos
            month = current_date.strftime('%m')  # Mês com 2 dígitos
            
            # Encontrar o próximo número sequencial para o mês atual
            prefix = f"CDF-{year_suffix}{month}-"
            
            # Consulta para encontrar o último código deste mês
            last_issue = Issue.query.filter(
                Issue.issue_code.like(f"{prefix}%")
            ).order_by(Issue.issue_code.desc()).first()
            
            if last_issue:
                # Extrair o número sequencial e incrementar
                last_number = int(last_issue.issue_code.split('-')[-1])
                next_number = last_number + 1
            else:
                # Primeiro registro do mês
                next_number = 1
            
            # Formatar o código final
            issue_code = f"{prefix}{next_number:04d}"
            
            # Processar upload da foto (se existir)
            photo_filename = None
            if 'photo' in request.files and request.files['photo'].filename:
                photo = request.files['photo']
                
                # Garantir que o nome é seguro
                original_filename = secure_filename(photo.filename)
                
                # Criar nome único para o arquivo com o código da ocorrência
                extension = os.path.splitext(original_filename)[1]
                photo_filename = f"{issue_code}{extension}"
                
                # Definir o caminho da pasta de uploads
                upload_folder = os.path.join(current_app.static_folder, 'uploads', 'issues')
                
                # Garantir que a pasta existe
                os.makedirs(upload_folder, exist_ok=True)
                
                # Caminho completo do arquivo
                photo_path = os.path.join(upload_folder, photo_filename)
                
                # Salvar o arquivo
                photo.save(photo_path)
            
            # Criar nova ocorrência
            new_issue = Issue(
                issue_code=issue_code,
                user_id=session['user_id'],
                category_id=category_id,
                # title=title,
                description=description,
                latitude=float(latitude),
                longitude=float(longitude),
                photo_filename=photo_filename,
                status='pendente'
            )
            
            # Salvar no banco de dados
            db.session.add(new_issue)
            db.session.commit()
            
            flash(f'Ocorrência {issue_code} reportada com sucesso!', 'success')
            return redirect(url_for('main.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao processar sua solicitação: {str(e)}', 'error')
            print(f"🪲 ERRO | {str(e)}")
            return redirect(url_for('main.report_issue'))
    
    return render_template('new_issue.html')

@main_bp.route('/view_issues')
def view_issues():
    """Página para visualizar ocorrências reportadas."""
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('auth.login'))

    return render_template('my_reports.html')
