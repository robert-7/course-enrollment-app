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


def test_api_get_put_delete_single_user(client):
    user = User(
        user_id=9,
        email="single@example.com",
        first_name="Single",
        last_name="User",
    )
    user.set_password("secret12")
    user.save()

    get_response = client.get("/api/9")
    assert get_response.status_code == 200
    assert get_response.get_json()[0]["email"] == "single@example.com"

    put_response = client.put(
        "/api/9",
        json={
            "first_name": "Updated",
            "last_name": "Name",
        },
    )
    assert put_response.status_code == 200
    assert put_response.get_json()[0]["first_name"] == "Updated"

    delete_response = client.delete("/api/9")
    assert delete_response.status_code == 200
    assert delete_response.get_json() == "User is deleted!"
    assert User.objects(user_id=9).count() == 0
