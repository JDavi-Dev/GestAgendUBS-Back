from os import getenv
from dotenv import load_dotenv
from datetime import timedelta

from flask_jwt_extended import JWTManager

from helpers.application import app
from helpers.database import db
from helpers.logging import logger

load_dotenv()

# ============================================
# CONFIGURAÇÕES JWT
# ============================================

app.config["JWT_SECRET_KEY"] = getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=8)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"
app.config["JWT_IDENTITY_CLAIM"] = "sub"

# Inicializar JWT
jwt = JWTManager(app)

# ============================================
# BLACKLIST (para tokens revogados)
# ============================================

# Estrutura simples de blacklist (em produção, use Redis)
_blacklist = set()

def add_token_to_blacklist(jti: str) -> None:
    """Adiciona um token à blacklist"""
    _blacklist.add(jti)
    logger.info(f"Token {jti} adicionado à blacklist")

def is_token_revoked(jti: str) -> bool:
    """Verifica se um token está na blacklist"""
    return jti in _blacklist

# Callback para verificar se token está revogado
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    return is_token_revoked(jti)

# ============================================
# CALLBACKS PERSONALIZADOS
# ============================================

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    """Resposta para token expirado"""
    return {"mensagem": "Token expirado. Faça login novamente."}, 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    """Resposta para token inválido"""
    return {"mensagem": "Token inválido."}, 401

@jwt.unauthorized_loader
def unauthorized_callback(error):
    """Resposta para token ausente"""
    return {"mensagem": "Token de autenticação é obrigatório."}, 401

@jwt.needs_fresh_token_loader
def needs_fresh_token_callback(jwt_header, jwt_payload):
    """Resposta quando é necessário token fresco (não refresh)"""
    return {"mensagem": "Token de acesso expirado. Use refresh token."}, 401

@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    """Resposta para token revogado"""
    return {"mensagem": "Token revogado. Faça login novamente."}, 401

# ============================================
# USER_LOADER (opcional - para carregar usuário)
# ============================================

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    """Carrega o usuário a partir do token (opcional)"""
    identity = jwt_data["sub"]
    from models.Credencial import Credencial
    from models.Paciente import Paciente
    from models.Profissional import Profissional
    from models.Administrador import Administrador
    
    # Buscar credencial pelo ID
    credencial = db.session.get(Credencial, identity)
    if not credencial:
        return None
    
    # Buscar o ator correspondente
    if credencial.tipo == 'paciente':
        return db.session.get(Paciente, credencial.referencia_id)
    elif credencial.tipo == 'profissional':
        return db.session.get(Profissional, credencial.referencia_id)
    else:
        return db.session.get(Administrador, credencial.referencia_id)