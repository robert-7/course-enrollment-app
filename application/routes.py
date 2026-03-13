import functools
import json
import os

from bson.json_util import RELAXED_JSON_OPTIONS
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import send_from_directory
from flask import session
from flask import url_for
from flask_restx import Resource

from application import api
from application import app
from application.course_list import course_list_for_user
from application.forms import LoginForm
from application.forms import RegisterForm
from application.models import Course
from application.models import Enrollment
from application.models import User


def login_required_api(f):
    """Reject unauthenticated requests to API endpoints with 401."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("username"):
            return {"error": "Authentication required"}, 401
        return f(*args, **kwargs)

    return wrapper


###################################################


@api.route("/courses", "/courses/")
class CoursesApi(Resource):
    method_decorators = [login_required_api]

    def get(self):
        courses = Course.objects.order_by("+courseID")
        return jsonify(json.loads(courses.to_json(json_options=RELAXED_JSON_OPTIONS)))


@api.route("/courses/<course_id>")
class CourseApi(Resource):
    method_decorators = [login_required_api]

    def get(self, course_id):
        course = Course.objects(courseID=course_id)
        if not course:
            return {"error": "Course not found"}, 404
        return jsonify(json.loads(course.to_json(json_options=RELAXED_JSON_OPTIONS)))


###################################################


@app.before_request
def redirect_root():
    """Redirects root to /home."""
    if request.path == "/":
        return redirect(url_for("index"))


@app.route("/api")
@app.route("/api/")
def api_root():
    """Redirect API root to interactive docs."""
    return redirect("/api/v1/docs")


@app.route("/home")
@app.route("/index")
def index():
    """Returns the landing page content."""
    return render_template("index.html", index=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Returns the login page content."""
    if session.get("username"):
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.objects(email=email).first()
        if user and user.get_password(password):
            flash("You are successfully logged in!", "success")
            session["user_id"] = user.user_id
            session["username"] = user.first_name
            return redirect("/index")
        else:
            flash("Sorry, something went wrong.", "danger")
    return render_template("login.html", title="Login", form=form, login=True)


@app.route("/logout")
def logout():
    session["user_id"] = False
    session.pop("username", None)
    return redirect(url_for("index"))


@app.route("/courses")
@app.route("/courses/<term>")
def courses(term=None):
    """Returns the courses page content."""
    if term is None:
        term = "Fall 2026"
    # Note: "+courseID" denotes sorting in increasing order by courseID
    classes = Course.objects.order_by("+courseID")
    return render_template("courses.html", courseData=classes, courses=True, term=term)


@app.route("/register", methods=["POST", "GET"])
def register():
    """Returns the registration page content."""
    if session.get("username"):
        return redirect(url_for("index"))
    form = RegisterForm()
    if form.validate_on_submit():
        user_id = User.objects.count()
        user_id += 1
        email = form.email.data
        password = form.password.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        user = User(
            user_id=user_id, email=email, first_name=first_name, last_name=last_name
        )
        user.set_password(password)
        user.save()
        flash("You are successfully registered!", "success")
        return redirect(url_for("index"))
    return render_template("register.html", title="Register", form=form, register=True)


@app.route("/enrollment", methods=["GET", "POST"])
def enrollment():
    """Returns the enrollment page content."""
    if not session.get("username"):
        return redirect(url_for("login"))

    courseID = request.form.get("courseID")
    courseTitle = request.form.get("title")
    user_id = session.get("user_id")

    # we check if we're coming from the course page here
    # if there's a courseID, it means we're enrolling in a course
    if courseID:
        if Enrollment.objects(user_id=user_id, courseID=courseID):
            flash(
                f"Oops! You are already registered in course {courseTitle}!",
                "danger",
            )
            return redirect(url_for("courses"))
        else:
            enrollment = Enrollment(user_id=user_id, courseID=courseID)
            enrollment.save()
            flash(f"You are enrolled in {courseTitle}!", "success")

    courses = course_list_for_user(user_id)
    return render_template(
        "enrollment.html",
        enrollment=True,
        title="Enrollment",
        classes=courses,
    )


@app.route("/favicon.ico")
def favicon():
    """Sends the favicon.ico file."""
    return send_from_directory(
        os.path.join(app.root_path, "static"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )
