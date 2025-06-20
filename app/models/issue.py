from app import db
from datetime import datetime

class Issue(db.Model):
    """Modelo para ocorrências reportadas pelos usuários."""
    id = db.Column(db.Integer, primary_key=True)
    issue_code = db.Column(db.String(15), unique=True, nullable=False)  # Código único CDF-202506-0018
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, nullable=False)
    # title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    photo_filename = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pendente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com o usuário
    user = db.relationship('User', backref=db.backref('issues', lazy=True))
    
    def __repr__(self):
        return f'<Issue {self.issue_code}>'