"""Route registration"""
from flask import Flask
from backend.routes.conversations import bp as conversations_bp
from backend.routes.messages import bp as messages_bp, init_chat_service
from backend.routes.models import bp as models_bp
from backend.routes.tools import bp as tools_bp
from backend.routes.stats import bp as stats_bp
from backend.routes.projects import bp as projects_bp
from backend.services.glm_client import GLMClient
from backend.config import API_URL, API_KEY


def register_routes(app: Flask):
    """Register all route blueprints"""
    # Initialize GLM client and chat service
    glm_client = GLMClient(API_URL, API_KEY)
    init_chat_service(glm_client)
    
    # Register blueprints
    app.register_blueprint(conversations_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(projects_bp)
