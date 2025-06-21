# app/utils/vision_analyzer.py

import os
import json
import base64
from openai import OpenAI
from app.utils.prompts.vision_prompts import CATEGORY_PROMPTS, RESPONSE_FORMAT
from app.utils.logger import log
from app.config.settings import Settings

class VisionAnalyzer:
    def __init__(self, api_key=None):
        # Configurar cliente OpenAI
        # TODO: Remover a chave de API fixa e usar variável de ambiente
        settings = Settings()
        self.api_key = settings.OPENAPI_API_KEY
        if not self.api_key:
            log.error("Chave da API OpenAI não encontrada! Configure a variável de ambiente OPENAI_API_KEY")
            raise ValueError("API key não configurada. Configure a variável de ambiente OPENAI_API_KEY")
            
        self.client = OpenAI(api_key=self.api_key)
        self.model = "gpt-4o"  # Modelo que suporta visão
        
    def _encode_image(self, image_path):
        """Codifica a imagem em base64 para envio à API."""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
            
    def analyze_image(self, image_path, category_id):
        """Analisa a imagem usando a API Vision e retorna resultado padronizado."""
        
        log.info(f"Analisando imagem com API Vision: {image_path} (categoria: {category_id})")
        
        # Buscar prompt adequado para a categoria
        prompt_config = CATEGORY_PROMPTS.get(category_id, CATEGORY_PROMPTS["default"])
        base64_image = self._encode_image(image_path)
        
        try:
            # Criar mensagem com prompt do sistema e usuário
            messages = [
                {
                    "role": "system",
                    "content": prompt_config["system_prompt"]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_config["user_prompt"] + "\n\n" + RESPONSE_FORMAT
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            log.debug("Enviando requisição para OpenAI API...")
            
            # Fazer a chamada à API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500
            )
            
            # Extrair o conteúdo da resposta
            ai_response = response.choices[0].message.content
            log.info("Resposta recebida da API Vision com sucesso")
            
            # Extrair o JSON da resposta
            try:
                if "```json" in ai_response:
                    json_str = ai_response.split("```json")[1].split("```")[0].strip()
                elif "```" in ai_response:
                    json_str = ai_response.split("```")[1].strip()
                else:
                    json_str = ai_response.strip()
                
                analysis_result = json.loads(json_str)
                
                # Adicionar metadados
                analysis_result["category_id"] = category_id
                analysis_result["threshold"] = prompt_config["confidence_threshold"]
                analysis_result["needs_review"] = (
                    not analysis_result.get("valid", False) or 
                    analysis_result.get("confidence", 0) < prompt_config["confidence_threshold"] or
                    analysis_result.get("needs_human_review", False)
                )
                
                log.info(f"Análise da imagem concluída: {json.dumps(analysis_result)}")
                return analysis_result
                
            except json.JSONDecodeError as e:
                log.error(f"Falha ao parsear JSON da resposta: {str(e)}")
                return {
                    "valid": False,
                    "error": f"Falha ao processar resposta da IA: {str(e)}",
                    "raw_response": ai_response[:500],
                    "needs_review": True
                }
                
        except Exception as e:
            log.error(f"Erro na chamada à API Vision: {str(e)}")
            return {
                "valid": False,
                "error": str(e),
                "needs_review": True
            }