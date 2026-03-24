import os
import yaml
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path

# Initialize db BEFORE importing models/routes that depend on it
db = SQLAlchemy()
CONFIG_PATH = Path(__file__).parent.parent / "config.yml"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_app():
    cfg = load_config()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"mysql+pymysql://{cfg['db_user']}:{cfg['db_password']}"
        f"@{cfg.get('db_host', 'localhost')}:{cfg.get('db_port', 3306)}/{cfg['db_name']}"
        f"?charset=utf8mb4"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Import after db is initialized
    from .models import User, Conversation, Message, TokenUsage
    from .routes import register_routes
    from .tools import init_tools

    register_routes(app)
    init_tools()

    with app.app_context():
        db.create_all()

    return app
