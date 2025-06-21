import click
from flask.cli import with_appcontext
import os

from app.models.user import User, UserRole

def create_admin(db):
    """
    Limpa os dados existentes e cria novas tabelas com um usuário admin inicial.
    """
    # 1. Cria todas as tabelas do banco de dados
    click.echo('Banco de dados inicializado e tabelas criadas.')

    # 2. Lógica para criar o primeiro usuário Analista (admin)
    ADMIN_USERNAME = os.environ.get('ADMIN_USER', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'admin')

    if not User.query.filter_by(username=ADMIN_USERNAME).first():
        admin_user = User(
            username=ADMIN_USERNAME,
            role=UserRole.ANALISTA
        )
        admin_user.set_password(ADMIN_PASSWORD)
        db.session.add(admin_user)
        db.session.commit()
        # click.echo(f"Usuário administrador '{ADMIN_USERNAME}' criado com sucesso.")
    else:
        click.echo(f"Usuário administrador '{ADMIN_USERNAME}' já existe.")