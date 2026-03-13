import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            'Generate one with: python -c "import secrets;'
            ' print(secrets.token_hex(32))"'
        )
    # MONGODB_SETTINGS is what Flask-MongoEngine looks for this conf key
    # for setting up the connection to the database.
    MONGODB_SETTINGS = {
        "db": "NOU_Enrollment",
        "host": os.environ.get("MONGO_URI"),
    }
