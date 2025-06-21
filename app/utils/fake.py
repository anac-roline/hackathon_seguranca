import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from faker import Faker
from app import db
from app.models.issue import Issue
from app.models.user import User, UserRole
from app import app  

# Configurar o Faker para português do Brasil
fake = Faker('pt_BR')

# Constantes
COMPANIES = [
    {"id": 1, "name": "terracap"},
    {"id": 2, "name": "Neoenergia"},
    {"id": 3, "name": "SLU"},
    {"id": 4, "name": "Caesb"},
]

CATEGORIES = {
    1: "Buraco na Via",
    2: "Iluminação Pública",
    3: "Lixo/Entulho",
    4: "Vazamento de Água/Esgoto"
}

# Mapeamento de categoria para empresa
CATEGORY_TO_COMPANY = {
    1: "terracap",
    2: "Neoenergia",
    3: "SLU",
    4: "Caesb"
}

# Coordenadas para diferentes regiões de Brasília
# Formato: [latitude_min, latitude_max, longitude_min, longitude_max]
BRASILIA_REGIONS = {
    "Plano Piloto": [-15.850, -15.750, -47.950, -47.850],
    "Taguatinga": [-15.850, -15.800, -48.080, -48.040],
    "Ceilândia": [-15.850, -15.800, -48.130, -48.090],
    "Sobradinho": [-15.670, -15.630, -47.850, -47.790],
    "Gama": [-16.040, -15.990, -48.080, -48.040]
}

# Descrições específicas para cada categoria
DESCRIPTIONS = {
    1: [  # Buraco na Via
        "Buraco profundo no asfalto, dificultando a passagem de veículos.",
        "Cratera formada após as chuvas, ocupando meia pista.",
        "Buraco de aproximadamente 40cm de diâmetro na via principal.",
        "Asfalto cedeu formando um buraco perigoso para motociclistas.",
        "Vários buracos sequenciais na pista, situação precária."
    ],
    2: [  # Iluminação Pública
        "Poste de iluminação com lâmpada queimada há mais de 2 semanas.",
        "Três postes sequenciais sem funcionamento, rua completamente escura.",
        "Fiação exposta em poste de iluminação, risco de curto-circuito.",
        "Poste danificado após batida de veículo, luminária pendurada.",
        "Iluminação piscando intermitentemente durante toda a noite."
    ],
    3: [  # Lixo/Entulho
        "Descarte irregular de entulho na calçada, impedindo passagem de pedestres.",
        "Acúmulo de lixo doméstico em terreno baldio, atraindo ratos e insetos.",
        "Grandes volumes de material de construção descartados irregularmente.",
        "Lixo espalhado próximo a ponto de ônibus sem lixeira.",
        "Móveis velhos abandonados na área verde há vários dias."
    ],
    4: [  # Vazamento de Água/Esgoto
        "Vazamento constante de água na calçada, desperdício visível.",
        "Esgoto a céu aberto próximo à área residencial, mau cheiro intenso.",
        "Água jorrando de hidrante quebrado, causando erosão no solo.",
        "Tampão de esgoto danificado com vazamento constante.",
        "Vazamento em tubulação de água potável, formando poça significativa."
    ]
}

# Status possíveis para as ocorrências
STATUS_OPTIONS = ["pendente", "em análise", "resolvido", "cancelado"]

def generate_issue_code() -> str:
    """Gera um código de ocorrência no formato CDF-YYYYMM-XXXX"""
    now = datetime.now()
    year_month = now.strftime("%Y%m")
    random_digits = ''.join(random.choices(string.digits, k=4))
    return f"CDF-{year_month}-{random_digits}"

def get_random_location(region: Optional[str] = None) -> tuple:
    """Retorna coordenadas aleatórias dentro de uma região especificada"""
    if region and region in BRASILIA_REGIONS:
        bounds = BRASILIA_REGIONS[region]
    else:
        # Escolhe uma região aleatória
        region = random.choice(list(BRASILIA_REGIONS.keys()))
        bounds = BRASILIA_REGIONS[region]
    
    lat = random.uniform(bounds[0], bounds[1])
    lng = random.uniform(bounds[2], bounds[3])
    
    return (lat, lng)

def get_image_filename(category_id: int) -> str:
    """Retorna um nome de arquivo de imagem baseado na categoria"""
    prefixes = {
        1: "buraco",
        2: "iluminacao",
        3: "lixo",
        4: "vazamento"
    }
    
    prefix = prefixes.get(category_id, "foto")
    num = random.randint(1, 10)
    return f"{prefix}_{num:02d}.jpg"

def generate_ai_validation_result(category_id: int) -> dict:
    """Gera um resultado fictício de validação por IA"""
    confidence = random.uniform(0.70, 0.98)
    valid = confidence > 0.85
    
    result = {
        "confidence": round(confidence, 4),
        "is_valid": valid,
        "matched_category": category_id if valid else random.choice([c for c in CATEGORIES.keys() if c != category_id]),
        "analysis_timestamp": datetime.now().isoformat(),
        "objects_detected": []
    }
    
    # Adiciona objetos detectados específicos por categoria
    if category_id == 1:  # Buraco
        result["objects_detected"] = ["asfalto_danificado", "buraco", "pavimento"]
    elif category_id == 2:  # Iluminação
        result["objects_detected"] = ["poste", "luminária", "fiação"]
    elif category_id == 3:  # Lixo
        result["objects_detected"] = ["entulho", "sacola", "material_descartado"]
    elif category_id == 4:  # Vazamento
        result["objects_detected"] = ["água", "vazamento", "tubulação"]
    
    return result

def create_fake_issues(count: int, user_id: int = None) -> List[Issue]:
    """
    Cria denúncias falsas mas realistas para teste.
    
    Args:
        count: Número de denúncias a serem criadas
        user_id: ID do usuário para associar às denúncias (opcional)
    
    Returns:
        Lista de objetos Issue criados
    """
    if user_id is None:
        # Verifica se já existe um usuário de teste
        test_user = User.query.filter_by(username="usuario_teste").first()
        
        if not test_user:
            # Cria um usuário de teste se não existir
            test_user = User(
                username="usuario_teste",
                role=UserRole.DENUNCIANTE
            )
            test_user.set_password("senha123")
            db.session.add(test_user)
            db.session.commit()
            
        user_id = test_user.id
    
    created_issues = []
    
    for _ in range(count):
        # Escolhe uma categoria aleatória
        category_id = random.choice(list(CATEGORIES.keys()))
        
        # Determina a empresa com base na categoria
        company = CATEGORY_TO_COMPANY[category_id]
        
        # Gera coordenadas aleatórias
        lat, lng = get_random_location()
        
        # Determina se a IA validou a denúncia
        ai_validated = random.random() > 0.2  # 80% de chance de ser validado
        
        # Gera resultado da validação por IA
        ai_result = generate_ai_validation_result(category_id) if ai_validated else None
        
        # Determina se precisa de revisão humana
        needs_review = not ai_validated or ai_result["confidence"] < 0.9 if ai_validated else True
        
        # Cria a data de criação (até 30 dias atrás)
        days_ago = random.randint(0, 30)
        created_date = datetime.now() - timedelta(days=days_ago)
        
        # Determina o status com base no tempo decorrido
        if days_ago < 3:
            status = "pendente"
        elif days_ago < 10:
            status = random.choice(["pendente", "em análise"])
        else:
            status = random.choice(STATUS_OPTIONS)
        
        # Cria a nova ocorrência
        issue = Issue(
            issue_code=generate_issue_code(),
            user_id=user_id,
            category_id=category_id,
            description=random.choice(DESCRIPTIONS[category_id]),
            latitude=lat,
            longitude=lng,
            photo_filename=get_image_filename(category_id),
            status=status,
            ai_validated=ai_validated,
            ai_validation_result=ai_result,
            needs_human_review=needs_review,
            human_reviewed=random.random() > 0.5 if needs_review else False,
            human_review_result=random.choice([True, False]) if needs_review and random.random() > 0.5 else None,
            companie=company,
            created_at=created_date,
            updated_at=created_date + timedelta(days=random.randint(0, min(5, days_ago)))
        )
        
        db.session.add(issue)
        created_issues.append(issue)
    
    # Commit todas as denúncias de uma vez
    db.session.commit()
    
    return created_issues

def generate_fake_data_cli():
    """Função CLI para gerar dados falsos"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Gerar dados falsos para o sistema de denúncias')
    parser.add_argument('--count', type=int, default=10, help='Número de denúncias a serem geradas')
    parser.add_argument('--user', type=int, help='ID do usuário para associar às denúncias')
    
    args = parser.parse_args()
    
    issues = create_fake_issues(args.count, args.user)
    print(f"Foram geradas {len(issues)} denúncias falsas com sucesso!")
    
    for issue in issues:
        print(f"- {issue.issue_code}: {CATEGORIES[issue.category_id]} ({issue.status})")

# Para executar diretamente como script
if __name__ == "__main__":
    with app.app_context():  
        generate_fake_data_cli()