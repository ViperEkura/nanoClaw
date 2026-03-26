import os
from pathlib import Path

import yaml
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Initialize db BEFORE importing models/routes that depend on it
db = SQLAlchemy()
CONFIG_PATH = Path(__file__).parent.parent / "config.yml"


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_database_uri(cfg: dict) -> str:
    """Build database URI based on database type."""
    db_type = cfg.get("db_type", "mysql").lower()

    if db_type == "sqlite":
        # SQLite: sqlite:///path/to/database.db
        db_file = cfg.get("db_sqlite_file", "nano_claw.db")
        # Store in workspace root directory (resolve relative to project root)
        project_root = CONFIG_PATH.parent
        workspace_root = project_root / cfg.get("workspace_root", "workspaces")
        workspace_root.mkdir(parents=True, exist_ok=True)
        db_path = workspace_root / db_file
        return f"sqlite:///{db_path.resolve()}"

    elif db_type == "postgresql":
        # PostgreSQL: postgresql://user:password@host:port/database
        return (
            f"postgresql://{cfg['db_user']}:{cfg['db_password']}"
            f"@{cfg.get('db_host', 'localhost')}:{cfg.get('db_port', 5432)}/{cfg['db_name']}"
        )

    else:  # mysql (default)
        # MySQL: mysql+pymysql://user:password@host:port/database?charset=utf8mb4
        return (
            f"mysql+pymysql://{cfg['db_user']}:{cfg['db_password']}"
            f"@{cfg.get('db_host', 'localhost')}:{cfg.get('db_port', 3306)}/{cfg['db_name']}"
            f"?charset=utf8mb4"
        )


def create_app():
    cfg = load_config()

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = _get_database_uri(cfg)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Enable CORS for all routes
    CORS(app)

    db.init_app(app)

    # Import after db is initialized
    from backend.models import User, Conversation, Message, TokenUsage, Project
    from backend.routes import register_routes
    from backend.tools import init_tools

    register_routes(app)
    init_tools()

    with app.app_context():
        db.create_all()

    return app
