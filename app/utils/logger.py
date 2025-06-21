import os
import logging
from datetime import datetime

class Logger:
    def __init__(self, log_file='app.log'):
        # Definir caminho do arquivo de log
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        self.log_path = os.path.join(log_dir, log_file)
        
        # Configurar o logger
        self.logger = logging.getLogger('cidade_fiscal')
        self.logger.setLevel(logging.DEBUG)
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            # Handler de arquivo
            file_handler = logging.FileHandler(self.log_path)
            file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            # Handler de console (opcional)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(file_formatter)
            self.logger.addHandler(console_handler)
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def warning(self, message):
        self.logger.warning(message)

# Instância global para uso fácil
log = Logger()