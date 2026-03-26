"""Authentication module - supports both single-user and multi-user modes.

Single-user mode (auth_mode: "single"):
  - Auto-creates a default user on first startup
  - All requests are authenticated as the default user (no token needed)
  - Login endpoint returns a convenience token but it's optional

Multi-user mode (auth_mode: "multi"):
  - Requires JWT token for all API requests (except login/register)
  - Users must register and login to get a token
  - Supports admin/user roles
"""
import time
import jwt
from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, request, g, current_app
from backend import db
from backend.models import User
from backend.utils.helpers import ok, err

bp = Blueprint("auth", __name__)

# Routes that don't require authentication
PUBLIC_ROUTES = {
    "POST:/api/auth/login",
    "POST:/api/auth/register",
    "GET:/api/models",
    "GET:/api/tools",
}


def get_auth_config():
    """Get auth configuration from app config."""
    return current_app.config.get("AUTH_CONFIG", {
        "mode": "single",  # "single" or "multi"
        "jwt_secret": "nano-claw-default-secret-change-in-production",
        "jwt_expiry": 7 * 24 * 3600,  # 7 days in seconds
    })


def generate_token(user):
    """Generate a JWT token for a user."""
    cfg = get_auth_config()
    payload = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": int(time.time()) + cfg["jwt_expiry"],
    }
    return jwt.encode(payload, cfg["jwt_secret"], algorithm="HS256")


def _resolve_user():
    """Resolve the current user from request context.

    In single-user mode: auto-creates and returns the default user.
    In multi-user mode: validates the JWT token from Authorization header.
    Returns None if authentication fails in multi-user mode.
    """
    cfg = get_auth_config()

    if cfg["mode"] == "single":
        user = User.query.filter_by(username="default").first()
        if not user:
            try:
                user = User(username="default", role="admin")
                db.session.add(user)
                db.session.commit()
            except Exception:
                db.session.rollback()
                user = User.query.filter_by(username="default").first()
        return user

    # Multi-user mode: validate JWT
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    try:
        payload = jwt.decode(token, cfg["jwt_secret"], algorithms=["HS256"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

    user = db.session.get(User, payload.get("user_id"))
    if not user or not user.is_active:
        return None
    return user


def init_auth(app):
    """Register authentication hooks on the Flask app."""
    cfg_path = app.config.get("AUTH_CONFIG_PATH")
    if cfg_path:
        from backend import load_config
        full_cfg = load_config()
        auth_mode = full_cfg.get("auth_mode", "single")
        jwt_secret = full_cfg.get("jwt_secret", "nano-claw-default-secret-change-in-production")
    else:
        auth_mode = "single"
        jwt_secret = "nano-claw-default-secret-change-in-production"

    app.config["AUTH_CONFIG"] = {
        "mode": auth_mode,
        "jwt_secret": jwt_secret,
        "jwt_expiry": 7 * 24 * 3600,
    }

    @app.before_request
    def before_request_auth():
        """Authenticate user before each request."""
        method_path = f"{request.method}:{request.path}"

        # Skip auth for public routes
        if method_path in PUBLIC_ROUTES:
            return None

        # Skip auth for static files
        if request.path.startswith("/static"):
            return None

        # In single-user mode, always set the default user
        cfg = get_auth_config()
        if cfg["mode"] == "single":
            g.current_user = _resolve_user()
            return None

        # Multi-user mode: validate token
        user = _resolve_user()
        if not user:
            return err(401, "Unauthorized - please login")
        g.current_user = user

        # Update last_login_at (debounced: at most once per hour)
        if (not user.last_login_at or
                (datetime.now(timezone.utc) - user.last_login_at).total_seconds() > 3600):
            user.last_login_at = datetime.now(timezone.utc)
            db.session.commit()

        return None


# --- Auth API Routes ---

@bp.route("/api/auth/login", methods=["POST"])
def login():
    """User login - returns JWT token."""
    cfg = get_auth_config()

    # Single-user mode: just return the default user's token
    if cfg["mode"] == "single":
        user = User.query.filter_by(username="default").first()
        if not user:
            return err(500, "Default user not initialized")
        return ok({
            "token": generate_token(user),
            "user": user.to_dict(),
        })

    # Multi-user mode: validate credentials
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return err(400, "Username and password are required")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return err(401, "Invalid username or password")

    if not user.is_active:
        return err(403, "Account is disabled")

    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()

    return ok({
        "token": generate_token(user),
        "user": user.to_dict(),
    })


@bp.route("/api/auth/register", methods=["POST"])
def register():
    """User registration - only available in multi-user mode."""
    cfg = get_auth_config()
    if cfg["mode"] == "single":
        return err(403, "Registration is disabled in single-user mode")

    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    email = data.get("email", "").strip() or None

    if not username or not password:
        return err(400, "Username and password are required")
    if len(username) < 2 or len(username) > 50:
        return err(400, "Username must be 2-50 characters")
    if len(password) < 4:
        return err(400, "Password must be at least 4 characters")
    if email and "@" not in email:
        return err(400, "Invalid email format")

    if User.query.filter_by(username=username).first():
        return err(409, f"Username '{username}' already exists")
    if email and User.query.filter_by(email=email).first():
        return err(409, "Email already registered")

    user = User(username=username, password=password, email=email)
    db.session.add(user)
    db.session.commit()

    return ok({
        "token": generate_token(user),
        "user": user.to_dict(),
    })


@bp.route("/api/auth/profile", methods=["GET"])
def get_profile():
    """Get current user profile."""
    user = getattr(g, "current_user", None)
    if not user:
        return err(401, "Not authenticated")
    return ok(user.to_dict())


@bp.route("/api/auth/profile", methods=["PATCH"])
def update_profile():
    """Update current user profile."""
    user = getattr(g, "current_user", None)
    if not user:
        return err(401, "Not authenticated")

    data = request.get_json(silent=True) or {}

    if "email" in data:
        new_email = data["email"].strip() or None
        if new_email and new_email != user.email:
            if User.query.filter_by(email=new_email).first():
                return err(409, "Email already registered")
        user.email = new_email

    if "avatar" in data:
        user.avatar = data["avatar"]

    if "password" in data:
        new_password = data["password"]
        if len(new_password) < 4:
            return err(400, "Password must be at least 4 characters")
        user.password = new_password

    db.session.commit()
    return ok(user.to_dict())


@bp.route("/api/auth/mode", methods=["GET"])
def get_auth_mode():
    """Get current authentication mode (public endpoint)."""
    cfg = get_auth_config()
    return ok({"mode": cfg["mode"]})
