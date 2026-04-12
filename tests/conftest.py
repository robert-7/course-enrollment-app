import os
import sys
from pathlib import Path

import mongoengine
import mongomock
import pytest

# Make sure the repository root is importable when pytest is run from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Set before importing the Flask app module, which connects at import-time.
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017/course_enrollment")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-production")

# Delayed imports are required: app initialization reads env/path at import-time.
from application import app  # noqa: E402
from application import limiter  # noqa: E402
from application.models import Course  # noqa: E402
from application.models import Enrollment  # noqa: E402
from application.models import User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _configure_test_db():
    mongoengine.disconnect()
    mongoengine.connect(
        db="course_enrollment_test",
        host="mongodb://localhost",
        alias="default",
        mongo_client_class=mongomock.MongoClient,
        uuidRepresentation="standard",
    )
    yield
    mongoengine.disconnect()


@pytest.fixture(autouse=True)
def _reset_collections():
    User.drop_collection()
    Course.drop_collection()
    Enrollment.drop_collection()


@pytest.fixture
def test_app():
    app.config.update(
        WTF_CSRF_ENABLED=False,
        RATELIMIT_ENABLED=False,
    )
    limiter.reset()
    limiter.enabled = False
    return app


@pytest.fixture
def client(test_app):
    return test_app.test_client()


@pytest.fixture
def seed_courses():
    courses = [
        Course(
            courseID="CSE100",
            title="Intro to Testing",
            description="Core testing patterns",
            credits=3,
            term="Fall 2026",
        ),
        Course(
            courseID="CSE200",
            title="Web Systems",
            description="HTTP and app architecture",
            credits=4,
            term="Fall 2026",
        ),
    ]
    for course in courses:
        course.save()
    return courses


@pytest.fixture
def registered_user():
    user = User(
        user_id=1,
        email="student@example.com",
        first_name="Sam",
        last_name="Student",
    )
    user.set_password("secret12")
    user.save()
    return user


@pytest.fixture
def logged_in_client(client, registered_user):
    with client.session_transaction() as session:
        session["user_id"] = registered_user.user_id
        session["username"] = registered_user.first_name
    return client
