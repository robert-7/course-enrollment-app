import os
from datetime import timedelta


def _get_secret_key():
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            'Generate one with: python -c "import secrets;'
            ' print(secrets.token_hex(32))"'
        )
    return secret_key


def _env_var_is_truthy(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    # Flask debug mode enables the interactive debugger and auto-reload.
    DEBUG = False
    # Flask testing mode enables test-friendly behavior in the framework.
    TESTING = False
    # Permanent sessions expire 30 minutes after their last refresh.
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    # Lax allows normal site navigation while reducing cross-site cookie sends.
    SESSION_COOKIE_SAMESITE = "Lax"
    # Secure cookies are sent only over HTTPS.
    SESSION_COOKIE_SECURE = False
    # HSTS tells browsers to use HTTPS for future requests to this site.
    ENABLE_HSTS = False
    # One year is a common baseline HSTS duration.
    HSTS_MAX_AGE = 31536000
    # CSP reduces XSS risk while allowing the current Bootstrap CDN and Swagger UI.
    CONTENT_SECURITY_POLICY = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    # Prevent content-type sniffing so browsers trust the declared MIME type.
    X_CONTENT_TYPE_OPTIONS = "nosniff"
    # Deny rendering the app inside a frame to reduce clickjacking risk.
    X_FRAME_OPTIONS = "DENY"

    def __init__(self):
        # SECRET_KEY signs session and CSRF data, so it must come from the env.
        self.SECRET_KEY = _get_secret_key()
        # MONGODB_SETTINGS is what Flask-MongoEngine looks for this conf key
        # for setting up the connection to the database.
        self.MONGODB_SETTINGS = {
            "db": "NOU_Enrollment",
            "host": os.environ.get("MONGO_URI"),
        }


class DevelopmentConfig(BaseConfig):
    SESSION_COOKIE_SECURE = False


class TestingConfig(BaseConfig):
    TESTING = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    ENABLE_HSTS = True
    SESSION_COOKIE_SECURE = True


_CONFIG_BY_ENV = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config_for_env():
    app_env = os.environ.get("APP_ENV", "").strip().lower() or "development"

    try:
        config_class = _CONFIG_BY_ENV[app_env]
    except KeyError as exc:
        supported_envs = ", ".join(sorted(_CONFIG_BY_ENV))
        raise RuntimeError(
            f"Unsupported APP_ENV value {app_env!r}. "
            f"Expected one of: {supported_envs}."
        ) from exc

    if app_env == "production" and _env_var_is_truthy("FLASK_DEBUG"):
        raise RuntimeError("FLASK_DEBUG must not be enabled when APP_ENV='production'.")

    return config_class()
