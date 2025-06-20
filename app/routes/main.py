from flask import Blueprint, render_template, flash, redirect, url_for, session

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