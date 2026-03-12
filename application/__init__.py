import mongoengine
from flask import Flask
from flask_restx import Api

from config import Config

# initiate the main web app
app = Flask(__name__)
app.config.from_object(Config)

# initiate the mongo engine
mongoengine.connect(
    db=app.config["MONGODB_SETTINGS"]["db"],
    host=app.config["MONGODB_SETTINGS"]["host"],
    uuidRepresentation="standard",
)

# initiate the API
api = Api(doc="/api/docs")
api.init_app(app)

from application import routes  # noqa: E402,F401
