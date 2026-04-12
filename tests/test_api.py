from application.models import Course


def test_api_root_redirects_to_docs(client):
    response = client.get("/api", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/api/v1/docs")


def test_api_docs_page_loads(client):
    response = client.get("/api/v1/docs")

    assert response.status_code == 200
    assert response.headers["Content-Security-Policy"].startswith("default-src 'self'")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


def test_api_courses_requires_auth(client):
    response = client.get("/api/v1/courses")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_api_course_by_id_requires_auth(client):
    response = client.get("/api/v1/courses/CSE100")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Authentication required"


def test_api_courses_lists_courses(logged_in_client):
    Course(
        courseID="CSE200",
        title="Web Systems",
        description="HTTP and app architecture",
        credits=4,
        term="Fall 2026",
    ).save()
    Course(
        courseID="CSE100",
        title="Intro to Testing",
        description="Core testing patterns",
        credits=3,
        term="Fall 2026",
    ).save()

    response = logged_in_client.get("/api/v1/courses")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 2
    assert payload[0]["courseID"] == "CSE100"
    assert payload[1]["courseID"] == "CSE200"


def test_api_course_by_id_returns_single_course(logged_in_client):
    Course(
        courseID="MTH101",
        title="Discrete Math",
        description="Logic and combinatorics",
        credits=3,
        term="Spring 2027",
    ).save()

    response = logged_in_client.get("/api/v1/courses/MTH101")

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["title"] == "Discrete Math"


def test_api_course_by_id_returns_404_for_missing_course(logged_in_client):
    response = logged_in_client.get("/api/v1/courses/NOPE999")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Course not found"


def test_api_courses_does_not_return_users(logged_in_client):
    response = logged_in_client.get("/api/v1/courses")

    assert response.status_code == 200
    assert response.get_json() == []
