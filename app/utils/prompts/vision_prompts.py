CATEGORY_PROMPTS = {
    1: {  # Buraco na Via
        "system_prompt": "Você é um especialista em análise de infraestrutura urbana focado em identificar problemas em vias públicas.",
        "user_prompt": "Analise esta imagem e determine se mostra um buraco ou deterioração em via pública (rua, calçada, estrada). Considere aspectos como: danos no asfalto, buracos, rachaduras significativas, afundamentos. Não considere pequenas imperfeições normais.",
        "expected_elements": ["buraco", "asfalto danificado", "rachadura", "via deteriorada"],
        "confidence_threshold": 0.7
    },
    2: {  # Iluminação Pública
        "system_prompt": "Você é um especialista em infraestrutura elétrica urbana e iluminação pública.",
        "user_prompt": "Analise esta imagem e determine se mostra um problema de iluminação pública como: poste sem luz, lâmpada quebrada, fiação exposta, luminária danificada ou poste caído/inclinado.",
        "expected_elements": ["poste", "lâmpada", "luminária", "fiação"],
        "confidence_threshold": 0.65
    },
    3:{ # Coleta de Lixo
        "system_prompt": "Você é um especialista em gestão de resíduos urbanos e coleta de lixo.",
        "user_prompt": "Analise esta imagem e determine se mostra um problema relacionado à coleta de lixo, como: acúmulo de lixo, entulho, falta de coleta, lixeira transbordando ou lixo espalhado.",
        "expected_elements": ["lixo", "entulho", "lixeira", "acúmulo"],
        "confidence_threshold": 0.7
        
    },
    4:{ # Agua / esgoto
        "system_prompt": "Você é um especialista em análise de problemas de água e esgoto urbanos.",
        "user_prompt": "Analise esta imagem e determine se mostra um problema relacionado a água ou esgoto, como: vazamento, entupimento, esgoto a céu aberto, poça d'água anormal. Não considere pequenas poças normais.",
        "expected_elements": ["vazamento", "entupimento", "poça d'água", "esgoto"],
        "confidence_threshold": 0.7
        
    },
    # Outras categorias...
    "default": {
        "system_prompt": "Você é um especialista em análise de problemas urbanos e infraestrutura pública.",
        "user_prompt": "Analise esta imagem e determine se ela mostra claramente um problema de infraestrutura urbana ou pública. A imagem deve mostrar claramente um problema que precisa ser resolvido pelo poder público.",
        "expected_elements": ["problema", "dano", "infraestrutura"],
        "confidence_threshold": 0.6
    }
}

# Formatar a resposta para consistência
RESPONSE_FORMAT = """
Responda em formato JSON com a seguinte estrutura:
{
  "valid": true/false,  # Se a imagem é válida para a categoria
  "confidence": 0.0-1.0,  # Seu nível de confiança na análise
  "matches_description": true/false,  # Se corresponde à descrição do problema
  "detected_elements": ["elemento1", "elemento2"],  # Elementos relevantes detectados
  "analysis": "Explicação breve da sua análise",
  "needs_human_review": true/false  # Se recomenda revisão humana
}
"""