from app import db
from datetime import datetime

class PromptFeedback(db.Model):
    """Armazena feedback para melhorar prompts de IA."""
    id = db.Column(db.Integer, primary_key=True)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    category_id = db.Column(db.Integer, nullable=False)
    ai_result = db.Column(db.JSON, nullable=False)
    human_result = db.Column(db.Boolean, nullable=False)
    feedback_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamento com a ocorrência
    issue = db.relationship('Issue', backref=db.backref('feedback', lazy=True))