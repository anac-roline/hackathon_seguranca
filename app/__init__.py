from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Inicializa a extensão
db = SQLAlchemy()

# Cria e configura o app
app = Flask(__name__)
app.config.from_object(Config)

# Inicializa o app com a extensão
db.init_app(app)

# Importa e registra os blueprints
from app.routes.main import main_bp
from app.routes.auth import auth_bp

app.register_blueprint(main_bp)
app.register_blueprint(auth_bp)

# Cria o banco de dados e as tabelas se não existirem
with app.app_context():
    db.create_all()