from application.models import Course
from application.models import Enrollment
from application.models import User


def test_user_password_hash_roundtrip():
    user = User(
        user_id=10,
        email="model@example.com",
        first_name="Model",
        last_name="Tester",
    )
    user.set_password("secure123")
    user.save()

    saved = User.objects.get(user_id=10)
    assert saved.password != "secure123"
    assert saved.get_password("secure123")
    assert not saved.get_password("badpass")


def test_course_persistence_fields():
    course = Course(
        courseID="MTH101",
        title="Discrete Math",
        description="Logic and combinatorics",
        credits=3,
        term="Spring 2027",
    )
    course.save()

    saved = Course.objects.get(courseID="MTH101")
    assert saved.title == "Discrete Math"
    assert saved.credits == 3


def test_enrollment_maps_user_to_course():
    user = User(
        user_id=20,
        email="enroll@example.com",
        first_name="Casey",
        last_name="Enroll",
    )
    user.set_password("secret12")
    user.save()

    course = Course(
        courseID="PHY100",
        title="Physics",
        description="Mechanics",
        credits=4,
        term="Fall 2026",
    )
    course.save()

    enrollment = Enrollment(user_id=user.user_id, courseID=course.courseID)
    enrollment.save()

    saved = Enrollment.objects.get(user_id=user.user_id, courseID=course.courseID)
    assert saved.user_id == 20
    assert saved.courseID == "PHY100"
