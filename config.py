import os
from dotenv import load_dotenv

# Load the variables from the .env file
load_dotenv()

class Config:
    # 1. Application Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-dev-key')
    
    # 2. Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False 
    
    # 3. JWT (Role-Based Authentication Settings)
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_COOKIE_SECURE = False 
    JWT_COOKIE_CSRF_PROTECT = True
    
    # 4. Performance (Caching)
    CACHE_TYPE = 'SimpleCache' 
    CACHE_DEFAULT_TIMEOUT = 300