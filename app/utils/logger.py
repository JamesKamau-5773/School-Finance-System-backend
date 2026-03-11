import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(app):
    if not os.path.exists('logs'):
        os.mkdir('logs')
        
    file_handler = RotatingFileHandler('logs/school_erp.log', maxBytes=10240000, backupCount=5)
    
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s (Line %(lineno)d): %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Smart School ERP Startup')