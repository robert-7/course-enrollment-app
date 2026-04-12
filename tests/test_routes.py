from application import limiter
from application.models import Enrollment
from application.models import User


def _session_cookie_header(response):
    for header in response.headers.getlist("Set-Cookie"):
        if header.startswith("session="):
            return header
    raise AssertionError("Expected a session cookie in the response")


def _post_from_ip(client, path, data, remote_addr, follow_redirects=False):
    return client.post(
        path,
        data=data,
        follow_redirects=follow_redirects,
        environ_overrides={"REMOTE_ADDR": remote_addr},
    )


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


def test_index_sets_security_headers(client):
    response = client.get("/index")

    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" not in response.headers


def test_index_sets_hsts_header_when_enabled(client, monkeypatch):
    monkeypatch.setitem(client.application.config, "ENABLE_HSTS", True)
    monkeypatch.setitem(client.application.config, "HSTS_MAX_AGE", 600)

    response = client.get("/index")

    assert response.headers["Strict-Transport-Security"] == "max-age=600"


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


def test_register_requires_valid_email_address(client):
    response = client.post(
        "/register",
        data={
            "email": "not-an-email",
            "password": "secret123",
            "password_confirm": "secret123",
            "first_name": "New",
            "last_name": "User",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Invalid email address." in response.data
    assert User.objects(email="not-an-email").count() == 0


def test_register_rejects_passwords_shorter_than_eight_characters(client):
    response = client.post(
        "/register",
        data={
            "email": "newuser@example.com",
            "password": "abc1234",
            "password_confirm": "abc1234",
            "first_name": "New",
            "last_name": "User",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"Field must be between 8 and 128 characters long." in response.data
    assert User.objects(email="newuser@example.com").count() == 0


def test_register_and_login_accept_long_passwords(client):
    long_password = "correct-horse-battery-staple-with-extra-entropy-1234567890"

    register_response = client.post(
        "/register",
        data={
            "email": "longpass@example.com",
            "password": long_password,
            "password_confirm": long_password,
            "first_name": "Long",
            "last_name": "Pass",
        },
        follow_redirects=False,
    )

    assert register_response.status_code == 302
    assert register_response.headers["Location"].endswith("/index")

    login_response = client.post(
        "/login",
        data={
            "email": "longpass@example.com",
            "password": long_password,
        },
        follow_redirects=False,
    )

    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/index")


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


def test_login_rate_limits_post_attempts(client, monkeypatch, registered_user):
    limiter.reset()
    monkeypatch.setattr(limiter, "enabled", True)

    for _ in range(5):
        response = _post_from_ip(
            client,
            "/login",
            data={
                "email": registered_user.email,
                "password": "wrongpass",
            },
            remote_addr="198.51.100.10",
            follow_redirects=False,
        )
        assert response.status_code == 200

    response = _post_from_ip(
        client,
        "/login",
        data={
            "email": registered_user.email,
            "password": "wrongpass",
        },
        remote_addr="198.51.100.10",
        follow_redirects=False,
    )

    assert response.status_code == 429


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
    with logged_in_client.session_transaction() as session:
        session["extra_key"] = "leftover"

    response = logged_in_client.get("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/index")

    with logged_in_client.session_transaction() as session:
        assert dict(session) == {}

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


def test_register_rate_limits_post_attempts(client, monkeypatch):
    limiter.reset()
    monkeypatch.setattr(limiter, "enabled", True)

    for _ in range(5):
        response = _post_from_ip(
            client,
            "/register",
            data={
                "email": "not-an-email",
                "password": "secret123",
                "password_confirm": "secret123",
                "first_name": "Rate",
                "last_name": "Limited",
            },
            remote_addr="198.51.100.11",
            follow_redirects=False,
        )
        assert response.status_code == 200

    response = _post_from_ip(
        client,
        "/register",
        data={
            "email": "not-an-email",
            "password": "secret123",
            "password_confirm": "secret123",
            "first_name": "Rate",
            "last_name": "Limited",
        },
        remote_addr="198.51.100.11",
        follow_redirects=False,
    )

    assert response.status_code == 429


def test_favicon_returns_icon(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 200
    assert response.content_type == "image/vnd.microsoft.icon"
