from flask import Blueprint, render_template, flash, redirect, url_for, request, session

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
        return redirect(url_for('login'))

    return render_template('dashboard.html')

@main_bp.route('/report_issue', methods=['GET', 'POST'])
def report_issue():
    """Página para reportar uma nova ocorrência."""
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Lógica para processar o formulário de reporte de ocorrência
        pass

    return render_template('new_issue.html')

