from functools import wraps
from flask import request
from flask_jwt_extended import (
    verify_jwt_in_request, 
    get_jwt_identity, 
    get_jwt,
    get_current_user
)
from helpers.database import db
from models.Credencial import Credencial


def token_required(f):
    """
    Decorator para proteger rotas com token JWT.
    Uso: @token_required
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Verifica se o token JWT está presente e válido
        verify_jwt_in_request()
        return f(*args, **kwargs)
    return decorated


def role_required(roles_allowed):
    """
    Decorator para verificar permissões por tipo de usuário.
    Uso: @role_required(['paciente', 'admin'])
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Primeiro verifica token
            verify_jwt_in_request()
            
            # Obtém claims do token
            claims = get_jwt()
            usuario_tipo = claims.get("tipo")
            
            if not usuario_tipo or usuario_tipo not in roles_allowed:
                return {
                    "mensagem": f"Acesso negado. Permissão necessária: {', '.join(roles_allowed)}"
                }, 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator


def paciente_required(f):
    """Decorator específico para rotas de paciente"""
    return role_required(['paciente'])(f)


def profissional_required(f):
    """Decorator específico para rotas de profissional"""
    return role_required(['profissional'])(f)


def admin_required(f):
    """Decorator específico para rotas de administrador"""
    return role_required(['administrador'])(f)


def get_current_credencial_id():
    """Função auxiliar para obter o ID da credencial do token atual"""
    try:
        return get_jwt_identity()
    except:
        return None


def get_current_usuario_tipo():
    """Função auxiliar para obter o tipo do usuário do token atual"""
    try:
        return get_jwt().get("tipo")
    except:
        return None


def get_current_referencia_id():
    """Função auxiliar para obter o ID de referência (ator) do token atual"""
    try:
        return get_jwt().get("referencia_id")
    except:
        return None