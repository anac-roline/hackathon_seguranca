from app import app, db
from app.models.user import User
from app.models.issue import Issue

def calcular_estatisticas():
    """Conecta ao banco e calcula as métricas de ocorrências."""
    with app.app_context():
        # Total de ocorrências reportadas
        ocorrencias_reportadas = Issue.query.count()
        
        # Ocorrências com status 'resolvido'
        # IMPORTANTE: Ajuste a string 'resolvido' se o seu status tiver outro nome
        ocorrencias_resolvidas = Issue.query.filter_by(status='resolvido').count()

        # Ocorrências com status 'em_andamento'
        # IMPORTANTE: Ajuste a string 'em_andamento' se o seu status tiver outro nome
        ocorrencias_em_andamento = Issue.query.filter_by(status='em_andamento').count()
        
        # Impacto Social: número de usuários únicos que reportaram ocorrências
        impacto_social = db.session.query(Issue.user_id).distinct().count()

        return {
            "ocorrencias_reportadas": ocorrencias_reportadas,
            "ocorrencias_resolvidas": ocorrencias_resolvidas,
            "ocorrencias_em_andamento": ocorrencias_em_andamento,
            "impacto_social": impacto_social
        }
