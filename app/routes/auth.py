from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models.user import User
from app.commands import create_admin

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Página de cadastro de novos usuários."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Verifica se o usuário já existe
        if User.query.filter_by(username=username).first():
            flash('Este nome de usuário já existe. Tente outro.', 'error')
            return redirect(url_for('auth.signup'))

        # Cria um novo usuário com senha hasheada
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Conta criada com sucesso! Faça o login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('signup.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login."""
    create_admin(db)
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        print(f"🪲 DEBUG | Dados recebidos - Usuário: {username}, Senha: {password}")

        user = User.query.filter_by(username=username).first()
        print(f"🪲 DEBUG | Verificando usuário - Usuário: {user}")

        # Verifica se o usuário existe e a senha está correta
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Login bem-sucedido! Bem-vindo, {user.username}!', 'success')
            return redirect(url_for('main.dashboard'))

        flash('Credenciais inválidas. Verifique seu usuário e senha.', 'error')
        return redirect(url_for('auth.login'))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Rota para fazer logout do usuário."""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Você foi desconectado.', 'info')
    
    return redirect(url_for('main.index'))