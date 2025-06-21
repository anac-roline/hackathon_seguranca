import requests
import json
from flask import current_app, render_template
from app import db

def get_location_data_from_coordinates(latitude, longitude):
    """
    Realiza geocodificação reversa para obter detalhes de endereço a partir de coordenadas
    usando a API do OpenStreetMap Nominatim.
    
    Args:
        latitude (float): Latitude da localização
        longitude (float): Longitude da localização
        
    Returns:
        dict: Dicionário contendo informações de endereço
    """
    try:
        # Usando o serviço gratuito Nominatim do OpenStreetMap
        # Nota: Para uso em produção, considere uma API paga como Google Maps ou Mapbox
        url = f"https://nominatim.openstreetmap.org/reverse?lat={latitude}&lon={longitude}&format=json"
        
        # Adicionar um User-Agent válido conforme requerido pelos termos de uso do Nominatim
        headers = {
            "User-Agent": "CidadeFiscal/1.0"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extrair dados do endereço
            address = data.get('address', {})
            
            # Estruturar os dados de localização
            location_data = {
                'street': address.get('road', ''),
                'house_number': address.get('house_number', ''),
                'neighborhood': address.get('suburb', '') or address.get('neighbourhood', ''),
                'city': address.get('city', '') or address.get('town', '') or address.get('village', ''),
                'state': address.get('state', ''),
                'postal_code': address.get('postcode', ''),
                'country': address.get('country', ''),
                'formatted_address': data.get('display_name', '')
            }
            
            # Construir o endereço completo
            if location_data['street'] and location_data['house_number']:
                location_data['street'] = f"{location_data['street']}, {location_data['house_number']}"
                
            return location_data
        else:
            current_app.logger.error(f"Erro na geocodificação reversa: {response.status_code}")
            return {}
            
    except Exception as e:
        current_app.logger.error(f"Erro ao obter dados de localização: {str(e)}")
        return {}


# Exemplo de como salvar os dados de localização no banco de dados
# Esta função poderia ser chamada ao criar uma nova ocorrência
def save_issue_with_location(issue):
    """
    Salva uma ocorrência e busca/armazena detalhes de localização
    """
    # Primeiro salva a ocorrência para obter o ID
    db.session.add(issue)
    db.session.commit()
    
    # Busca dados de localização
    location_data = get_location_data_from_coordinates(issue.latitude, issue.longitude)
    
    # Se você tiver um modelo Location, poderia criar um registro
    # Exemplo:
    # location = Location(
    #     issue_id=issue.id,
    #     street=location_data.get('street', ''),
    #     neighborhood=location_data.get('neighborhood', ''),
    #     city=location_data.get('city', ''),
    #     postal_code=location_data.get('postal_code', ''),
    #     state=location_data.get('state', ''),
    #     formatted_address=location_data.get('formatted_address', '')
    # )
    # db.session.add(location)
    # db.session.commit()
    
    # Ou você poderia armazenar como JSON na própria ocorrência
    # issue.location_data = json.dumps(location_data)
    # db.session.commit()
    
    return issue