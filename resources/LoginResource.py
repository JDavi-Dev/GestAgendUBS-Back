from flask import request
from flask_restful import Resource

from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, get_jwt

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta

from helpers.database import db
from helpers.logging import logger, log_exception
from helpers.jwt import add_token_to_blacklist

from models.Credencial import Credencial

# Rate limiting para proteção contra brute force
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

class LoginResource(Resource):

    @limiter.limit("5 per minute")
    def post(self):

        logger.info("POST - Login")

        # Valida JSON
        if not request.is_json:
            return {"mensagem": "JSON obrigatório"}, 400

        dados = request.get_json(silent=True) or {}

        login = dados.get("login")
        senha = dados.get("senha")

        # Valida credenciais
        if not login or not senha:
            return {"mensagem": "Credenciais inválidas"}, 401
            # return {"mensagem": "Login (CPF ou email) e senha são obrigatórios."}, 400

        try:

            # Busca credencial pelo login
            credencial = db.session.execute(
                db.select(Credencial).where(Credencial.login == login)
            ).scalar_one_or_none()

            # Credencial não encontrada
            if not credencial:
                logger.warning(f"Login não encontrado: {login}")
                return {"mensagem": "Credenciais inválidas"}, 401

            # Credencial inativa
            if not credencial.ativo:
                logger.warning(f"Credencial inativa: {login}")
                return {"mensagem": "Credenciais inválidas"}, 401

            # Senha inválida
            if not credencial.verificar_senha(senha):
                logger.warning(f"Senha incorreta: {login}")
                return {"mensagem": "Credenciais inválidas"}, 401

            # Claims adicionais do JWT
            additional_claims = {
                "login": credencial.login,
                "tipo": credencial.tipo,
                "referencia_id": credencial.referencia_id,
            }

            # Gera tokens
            access_token = create_access_token(
                identity=str(credencial.id), 
                additional_claims=additional_claims,
                expires_delta=timedelta(hours=8)
            )

            refresh_token = create_refresh_token(identity=str(credencial.id), additional_claims=additional_claims)

            logger.info(f"Login realizado: {credencial.login} ({credencial.tipo})")

            return {
                "mensagem": "Login realizado com sucesso",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "credencial": {
                    "id": credencial.id,
                    "login": credencial.login,
                    "tipo": credencial.tipo,
                    "referencia_id": credencial.referencia_id,
                    "ativo": credencial.ativo,
                },
            }, 200

        except Exception:
            log_exception("Erro inesperado no login")
            return {"mensagem": "Erro interno do servidor"}, 500

class RefreshTokenResource(Resource):
    """Endpoint para renovar access token usando refresh token"""
    
    @jwt_required(refresh=True)  # Exige refresh token
    def post(self):
        
        logger.info("POST - Refresh Token")
        
        try:
            # Obter identidade do refresh token
            credencial_id = get_jwt_identity()
            
            # Buscar credencial
            credencial = db.session.get(Credencial, credencial_id)
            
            if not credencial or not credencial.ativo:
                return {"mensagem": "Credencial inválida ou inativa."}, 401

            additional_claims = {
                "login": credencial.login,
                "tipo": credencial.tipo,
                "referencia_id": credencial.referencia_id,
            }
            
            # Criar novo access token
            new_access_token = create_access_token(identity=str(credencial.id), additional_claims=additional_claims)
            
            return {
                "mensagem": "Token renovado com sucesso.",
                "access_token": new_access_token
            }, 200
            
        except Exception:
            log_exception("Erro ao renovar token")
            return {"mensagem": "Ocorreu um erro inesperado."}, 500

class LogoutResource(Resource):
    """Endpoint para logout (revogar tokens)"""
    
    @jwt_required()
    def post(self):
        logger.info("POST - Logout")
        
        try:
            # Obter JTI (JWT ID) do token e adicionar à blacklist
            jti = get_jwt()["jti"]
            add_token_to_blacklist(jti)
            
            logger.info(f"Token {jti} revogado com sucesso")
            return {"mensagem": "Logout realizado com sucesso."}, 200
            
        except Exception:
            log_exception("Erro ao fazer logout")
            return {"mensagem": "Ocorreu um erro inesperado."}, 500