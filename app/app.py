import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24) # Chave secreta essencial para a segurança da sessão
# --- ALTERAÇÃO AQUI ---
# Define o diretório base da aplicação
basedir = os.path.abspath(os.path.dirname(__file__))
# Define o caminho para a pasta de instância
instance_path = os.path.join(basedir, 'instance')

# Garante que a pasta de instância exista
os.makedirs(instance_path, exist_ok=True)

# Configura a URI do banco de dados com o caminho absoluto
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(instance_path, 'site.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Modelo do Banco de Dados ---
class User(db.Model):
    """Modelo de usuário para o banco de dados."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# --- Rotas da Aplicação ---
@app.route('/')
def index():
    """Página inicial."""
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Página de cadastro de novos usuários."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Verifica se o usuário já existe
        if User.query.filter_by(username=username).first():
            flash('Este nome de usuário já existe. Tente outro.', 'error')
            return redirect(url_for('signup'))

        # Cria um novo usuário com senha hasheada
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password, method='pbkdf2:sha256')
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Conta criada com sucesso! Faça o login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        # Verifica se o usuário existe e a senha está correta
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Login bem-sucedido! Bem-vindo, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Credenciais inválidas. Verifique seu usuário e senha.', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Painel de controle, acessível apenas para usuários logados."""
    if 'user_id' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('login'))
    
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    """Rota para fazer logout do usuário."""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Você foi desconectado.', 'info')
    return redirect(url_for('index'))

# --- Execução da Aplicação ---
if __name__ == '__main__':
    # Cria o banco de dados e as tabelas se não existirem
    with app.app_context():
        db.create_all()
    app.run(debug=True)