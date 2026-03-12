from application.models import User


def test_api_get_returns_all_users(client):
    user = User(
        user_id=1,
        email="apiuser@example.com",
        first_name="Api",
        last_name="User",
    )
    user.set_password("secret12")
    user.save()

    response = client.get("/api")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["email"] == "apiuser@example.com"


def test_api_post_creates_user(client):
    response = client.post(
        "/api",
        json={
            "user_id": 2,
            "email": "newapi@example.com",
            "first_name": "New",
            "last_name": "Api",
            "password": "secret12",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload[0]["user_id"] == 2
    assert payload[0]["email"] == "newapi@example.com"
    assert payload[0]["password"] != "secret12"


def test_api_post_rejects_duplicate_user_id(client):
    user = User(
        user_id=4,
        email="dup1@example.com",
        first_name="Dup",
        last_name="One",
    )
    user.set_password("secret12")
    user.save()

    response = client.post(
        "/api",
        json={
            "user_id": 4,
            "email": "dup2@example.com",
            "first_name": "Dup",
            "last_name": "Two",
            "password": "secret12",
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "User ID already exists"


def test_api_post_rejects_duplicate_email(client):
    user = User(
        user_id=5,
        email="taken@example.com",
        first_name="First",
        last_name="Owner",
    )
    user.set_password("secret12")
    user.save()

    response = client.post(
        "/api",
        json={
            "user_id": 6,
            "email": "taken@example.com",
            "first_name": "Second",
            "last_name": "Owner",
            "password": "secret12",
        },
    )

    assert response.status_code == 409
    assert response.get_json()["error"] == "Email already exists"


def _create_user(user_id=9, email="single@example.com"):
    user = User(
        user_id=user_id,
        email=email,
        first_name="Single",
        last_name="User",
    )
    user.set_password("secret12")
    user.save()
    return user


def test_api_get_single_user(client):
    _create_user()

    response = client.get("/api/9")

    assert response.status_code == 200
    assert response.get_json()[0]["email"] == "single@example.com"


def test_api_put_updates_user(client):
    _create_user()

    response = client.put(
        "/api/9",
        json={
            "first_name": "Updated",
            "last_name": "Name",
        },
    )

    assert response.status_code == 200
    assert response.get_json()[0]["first_name"] == "Updated"
    assert response.get_json()[0]["last_name"] == "Name"


def test_api_delete_removes_user(client):
    _create_user()

    response = client.delete("/api/9")

    assert response.status_code == 200
    assert response.get_json() == "User is deleted!"
    assert User.objects(user_id=9).count() == 0
