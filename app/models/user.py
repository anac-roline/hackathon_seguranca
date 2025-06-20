# Importe as bibliotecas necessárias no início do seu arquivo
import enum
from app import db # Supondo que 'db' seja sua instância do SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# 1. Defina os papéis usando a classe Enum do Python para maior segurança e clareza
class UserRole(enum.Enum):
    """Define os papéis/funções possíveis para um usuário."""
    DENUNCIANTE = 'denunciante' # Usuário que pode criar denúncias
    ANALISTA = 'analista'     # Usuário que pode visualizar e analisar os dados

# 2. Atualize seu modelo de Usuário
class User(db.Model):
    """Modelo de usuário para o banco de dados com papéis e gerenciamento de senha."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    # --- NOVO CAMPO: ROLE ---
    # Armazena o papel do usuário. O valor padrão para qualquer novo usuário é 'denunciante'.
    role = db.Column(
        db.Enum(UserRole), 
        nullable=False, 
        default=UserRole.DENUNCIANTE
    )

    # --- MÉTODOS DE SENHA (BOA PRÁTICA) ---
    def set_password(self, password):
        """Gera o hash da senha e o armazena no banco de dados."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return check_password_hash(self.password_hash, password)

    # --- PROPRIEDADES AUXILIARES (HELPER PROPERTIES) ---
    # Facilitam a verificação de papéis no código da sua aplicação.
    @property
    def is_analista(self):
        return self.role == UserRole.ANALISTA

    @property
    def is_denunciante(self):
        return self.role == UserRole.DENUNCIANTE

    def __repr__(self):
        return f'<User {self.username} ({self.role.value})>'