from application.models import Enrollment
from application.models import User


def _session_cookie_header(response):
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith("session="):
            return header
    raise AssertionError("Expected a session cookie in the response")


def test_index_page_loads(client):
    response = client.get("/index")

    assert response.status_code == 200


def test_home_page_loads(client):
    response = client.get("/home")

    assert response.status_code == 200


def test_root_redirects_to_index(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/index")


def test_courses_route_renders_courses(client, seed_courses):
    response = client.get("/courses")

    assert response.status_code == 200
    assert b"Course Offerings" in response.data
    assert b"Intro to Testing" in response.data


def test_register_creates_user_and_redirects(client):
    response = client.post(
        "/register",
        data={
            "email": "newuser@example.com",
            "password": "secret12",
            "password_confirm": "secret12",
            "first_name": "New",
            "last_name": "User",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/index")
    assert User.objects(email="newuser@example.com").count() == 1


def test_login_success_sets_session_and_redirects(client, registered_user):
    response = client.post(
        "/login",
        data={
            "email": registered_user.email,
            "password": "secret12",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/index")


def test_login_sets_secure_cookie_attribute_when_enabled(
    client, monkeypatch, registered_user
):
    monkeypatch.setitem(client.application.config, "SESSION_COOKIE_SECURE", True)

    response = client.post(
        "/login",
        data={
            "email": registered_user.email,
            "password": "secret12",
        },
        follow_redirects=False,
    )

    assert "Secure;" in _session_cookie_header(response)


def test_login_omits_secure_cookie_attribute_when_disabled(
    client, monkeypatch, registered_user
):
    monkeypatch.setitem(client.application.config, "SESSION_COOKIE_SECURE", False)

    response = client.post(
        "/login",
        data={
            "email": registered_user.email,
            "password": "secret12",
        },
        follow_redirects=False,
    )

    assert "Secure;" not in _session_cookie_header(response)


def test_login_sets_lax_samesite_cookie_attribute(client, registered_user):
    response = client.post(
        "/login",
        data={
            "email": registered_user.email,
            "password": "secret12",
        },
        follow_redirects=False,
    )

    assert "SameSite=Lax" in _session_cookie_header(response)


def test_login_marks_session_permanent_and_sets_expiry_cookie(client, registered_user):
    response = client.post(
        "/login",
        data={
            "email": registered_user.email,
            "password": "secret12",
        },
        follow_redirects=False,
    )

    with client.session_transaction() as session:
        assert session.permanent is True

    assert "Expires=" in _session_cookie_header(response)


def test_login_failure_shows_error(client, registered_user):
    response = client.post(
        "/login",
        data={
            "email": registered_user.email,
            "password": "wrongpass",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Sorry, something went wrong." in response.data


def test_enrollment_requires_login(client):
    response = client.get("/enrollment", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_enrollment_creates_record_for_logged_in_user(logged_in_client, seed_courses):
    response = logged_in_client.post(
        "/enrollment",
        data={
            "courseID": "CSE100",
            "title": "Intro to Testing",
            "term": "Fall 2026",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You are enrolled in Intro to Testing!" in response.data
    assert Enrollment.objects(user_id=1, courseID="CSE100").count() == 1


def test_duplicate_enrollment_shows_error(logged_in_client, seed_courses):
    Enrollment(user_id=1, courseID="CSE100").save()

    response = logged_in_client.post(
        "/enrollment",
        data={
            "courseID": "CSE100",
            "title": "Intro to Testing",
            "term": "Fall 2026",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Oops! You are already registered in course" in response.data


def test_courses_with_explicit_term(client, seed_courses):
    response = client.get("/courses/Spring 2027")

    assert response.status_code == 200
    assert b"Spring 2027" in response.data


def test_logout_clears_session_and_redirects(logged_in_client):
    response = logged_in_client.get("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/index")

    response = logged_in_client.get("/enrollment", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_redirects_when_already_logged_in(logged_in_client):
    response = logged_in_client.get("/login", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/index")


def test_register_redirects_when_already_logged_in(logged_in_client):
    response = logged_in_client.get("/register", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/index")


def test_register_get_renders_form(client):
    response = client.get("/register")

    assert response.status_code == 200
    assert b"Register" in response.data


def test_register_duplicate_email_renders_form_with_error(client, registered_user):
    response = client.post(
        "/register",
        data={
            "email": registered_user.email,
            "password": "secret12",
            "password_confirm": "secret12",
            "first_name": "Adam",
            "last_name": "Smith",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Email is already in user" in response.data


def test_favicon_returns_icon(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.content_type == "image/vnd.microsoft.icon"
