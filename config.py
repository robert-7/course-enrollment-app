import os


class Config:
    SECRET_KEY = (
        os.environ.get("SECRET_KEY")
        or b"z\xcf4\xb6\x19\xadA\xd8&\xd4\x10\xb2\xf4\xf0T\xcc"
    )
    # MONGODB_SETTINGS is what Flask-MongoEngine looks for this conf key
    # for setting up the connection to the database.
    MONGODB_SETTINGS = {
        "db": "NOU_Enrollment",
        "host": os.environ.get("MONGO_URI"),
    }
