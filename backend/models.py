from datetime import datetime, timezone
from sqlalchemy.dialects.mysql import LONGTEXT
from backend import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))

    conversations = db.relationship("Conversation", backref="user", lazy="dynamic",
                                    cascade="all, delete-orphan",
                                    order_by="Conversation.updated_at.desc()")


class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(255), nullable=False, default="")
    model = db.Column(db.String(64), nullable=False, default="glm-5")
    system_prompt = db.Column(db.Text, default="")
    temperature = db.Column(db.Float, nullable=False, default=1.0)
    max_tokens = db.Column(db.Integer, nullable=False, default=65536)
    thinking_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = db.relationship("Message", backref="conversation", lazy="dynamic",
                               cascade="all, delete-orphan",
                               order_by="Message.created_at.asc()")


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.String(64), primary_key=True)
    conversation_id = db.Column(db.String(64), db.ForeignKey("conversations.id"), nullable=False)
    role = db.Column(db.String(16), nullable=False)  # user, assistant, system, tool
    content = db.Column(db.Text, default="")
    token_count = db.Column(db.Integer, default=0)
    thinking_content = db.Column(db.Text, default="")
    
    # Tool call support
    tool_calls = db.Column(LONGTEXT)  # JSON string: tool call requests (assistant messages)
    tool_call_id = db.Column(db.String(64))  # Tool call ID (tool messages)
    name = db.Column(db.String(64))  # Tool name (tool messages)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class TokenUsage(db.Model):
    __tablename__ = "token_usage"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)  # 使用日期
    model = db.Column(db.String(64), nullable=False)  # 模型名称
    prompt_tokens = db.Column(db.Integer, default=0)
    completion_tokens = db.Column(db.Integer, default=0)
    total_tokens = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", "model", name="uq_user_date_model"),
    )
