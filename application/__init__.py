import mongoengine
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_restx import Api
from flask_wtf.csrf import CSRFProtect

from config import get_config_for_env

# initiate the main web app
app = Flask(__name__)
app.config.from_object(get_config_for_env())
app.config.setdefault("RATELIMIT_STORAGE_URI", "memory://")

# enable CSRF protection for all POST forms
csrf = CSRFProtect(app)

# rate limit authentication POSTs without requiring extra infra in development
limiter = Limiter(key_func=get_remote_address)
limiter.init_app(app)

# initiate the mongo engine
mongoengine.connect(
    db=app.config["MONGODB_SETTINGS"]["db"],
    host=app.config["MONGODB_SETTINGS"]["host"],
    uuidRepresentation="standard",
)

# initiate the API
api = Api(prefix="/api/v1", doc="/api/v1/docs")
api.init_app(app)


@app.after_request
def apply_security_headers(response):
    response.headers["Content-Security-Policy"] = app.config["CONTENT_SECURITY_POLICY"]
    response.headers["X-Content-Type-Options"] = app.config["X_CONTENT_TYPE_OPTIONS"]
    response.headers["X-Frame-Options"] = app.config["X_FRAME_OPTIONS"]

    if app.config["ENABLE_HSTS"]:
        response.headers["Strict-Transport-Security"] = (
            f"max-age={app.config['HSTS_MAX_AGE']}"
        )

    return response


from application import routes  # noqa: E402,F401
