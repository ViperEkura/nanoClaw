from backend import db
from datetime import datetime, timezone
from flask import current_app
from sqlalchemy import Text
from sqlalchemy.dialects.mysql import LONGTEXT as MYSQL_LONGTEXT



def get_longtext_type():
    """Get appropriate text type for long content based on database dialect."""
    db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("mysql"):
        return MYSQL_LONGTEXT
    return Text  # SQLite and PostgreSQL use Text


# For model definitions, we'll use a callable that returns the right type
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
    password = db.Column(db.String(255), nullable=True)  # Allow NULL for third-party login
    phone = db.Column(db.String(20))

    conversations = db.relationship("Conversation", backref="user", lazy="dynamic",
                                    cascade="all, delete-orphan",
                                    order_by="Conversation.updated_at.desc()")


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
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
    content = db.Column(LongText, default="")  # LongText for long conversations
    token_count = db.Column(db.Integer, default=0)
    thinking_content = db.Column(LongText, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Tool call support - relation to ToolCall table
    tool_calls = db.relationship("ToolCall", backref="message", lazy="dynamic",
                                 cascade="all, delete-orphan",
                                 order_by="ToolCall.call_index.asc()")


class ToolCall(db.Model):
    """Tool call record - separate table, follows database normalization"""
    __tablename__ = "tool_calls"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message_id = db.Column(db.String(64), db.ForeignKey("messages.id"), 
                           nullable=False, index=True)
    call_id = db.Column(db.String(64), nullable=False)  # Tool call ID
    call_index = db.Column(db.Integer, nullable=False, default=0)  # Call order
    tool_name = db.Column(db.String(64), nullable=False)  # Tool name
    arguments = db.Column(LongText, nullable=False)  # Call arguments JSON
    result = db.Column(LongText)  # Execution result JSON
    execution_time = db.Column(db.Float, default=0)  # Execution time (seconds)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index("ix_tool_calls_message_call", "message_id", "call_index"),
    )


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
