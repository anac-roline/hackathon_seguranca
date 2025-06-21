import os

# Define o diretório base da aplicação
basedir = os.path.abspath(os.path.dirname(__file__))
# Define o caminho para a pasta de instância
instance_path = os.path.join(basedir, 'instance')

# Garante que a pasta de instância exista
os.makedirs(instance_path, exist_ok=True)

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(instance_path, 'site.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False