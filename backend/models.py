from backend import db
from datetime import datetime, timezone
from sqlalchemy import Text
from sqlalchemy.dialects.mysql import LONGTEXT as MYSQL_LONGTEXT



class LongText(db.TypeDecorator):
    """Cross-database LONGTEXT type that works with MySQL, SQLite, and PostgreSQL."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(MYSQL_LONGTEXT)
        return dialect.type_descriptor(Text)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # NULL for API-key-only auth
    email = db.Column(db.String(120), unique=True, nullable=True)
    avatar = db.Column(db.String(512), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="user")  # user, admin
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login_at = db.Column(db.DateTime, nullable=True)

    conversations = db.relationship("Conversation", backref="user", lazy="dynamic",
                                    cascade="all, delete-orphan",
                                    order_by="Conversation.updated_at.desc()")
    projects = db.relationship("Project", backref="user", lazy="dynamic",
                               cascade="all, delete-orphan")

    @property
    def password(self):
        raise AttributeError("password is not readable")

    @password.setter
    def password(self, plain):
        if plain:
            from werkzeug.security import generate_password_hash
            self.password_hash = generate_password_hash(plain)
        else:
            self.password_hash = None

    def check_password(self, plain):
        if not self.password_hash:
            return False
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, plain)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "avatar": self.avatar,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    project_id = db.Column(db.String(64), db.ForeignKey("projects.id"), nullable=True, index=True)
    title = db.Column(db.String(255), nullable=False, default="")
    model = db.Column(db.String(64), nullable=False, default="glm-5")
    system_prompt = db.Column(db.Text, default="")
    temperature = db.Column(db.Float, nullable=False, default=1.0)
    max_tokens = db.Column(db.Integer, nullable=False, default=65536)
    thinking_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc), index=True)

    messages = db.relationship("Message", backref="conversation", lazy="dynamic",
                               cascade="all, delete-orphan",
                               order_by="Message.created_at.asc()")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.String(64), primary_key=True)
    conversation_id = db.Column(db.String(64), db.ForeignKey("conversations.id"), 
                                nullable=False, index=True)
    role = db.Column(db.String(16), nullable=False)  # user, assistant, system, tool
    # Unified JSON structure:
    # User: {"text": "...", "attachments": [{"name": "a.py", "extension": "py", "content": "..."}]}
    # Assistant: {"text": "...", "thinking": "...", "tool_calls": [{"id": "...", "name": "...", "arguments": "...", "result": "..."}]}
    content = db.Column(LongText, default="")
    token_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class TokenUsage(db.Model):
    __tablename__ = "token_usage"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), 
                        nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    model = db.Column(db.String(64), nullable=False)
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", "model", name="uq_user_date_model"),
        db.Index("ix_token_usage_date_model", "date", "model"),  # Composite index
    )


class Project(db.Model):
    """Project model for workspace isolation"""
    __tablename__ = "projects"

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(512), nullable=False)  # Relative path within workspace root
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))

    # Relationship: one project can have multiple conversations
    conversations = db.relationship("Conversation", backref="project", lazy="dynamic",
                                   cascade="all, delete-orphan")

    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_user_project_name"),
    )
