"""Route registration"""
from flask import Flask
from backend.routes.conversations import bp as conversations_bp
from backend.routes.messages import bp as messages_bp, init_chat_service
from backend.routes.models import bp as models_bp
from backend.routes.tools import bp as tools_bp
from backend.routes.stats import bp as stats_bp
from backend.routes.projects import bp as projects_bp
from backend.routes.auth import bp as auth_bp, init_auth
from backend.services.llm_client import LLMClient
from backend.config import MODEL_CONFIG


def register_routes(app: Flask):
    """Register all route blueprints"""
    # Initialize LLM client with per-model config
    client = LLMClient(MODEL_CONFIG)
    init_chat_service(client)

    # Register LLM client in service locator so tools (e.g. multi_agent) can access it
    from backend.tools import register_service
    register_service("llm_client", client)

    # Initialize authentication system (reads auth_mode from config.yml)
    init_auth(app)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(projects_bp)
