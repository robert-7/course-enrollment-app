# Testing

Assuming was started correctly, when implementing changes, here is an end-to-end
test-case for assessing whether everything works:

1. Follow the steps in [CONTRIBUTING.md](CONTRIBUTING.md), then bring up the environment with `docker compose up -d --build`.
1. Go to [home page](http://127.0.0.1:5000/index). The web page should load.
1. Go to [the courses page](http://127.0.0.1:5000/courses).
   The web page should load and show 5 courses.
1. Go to [the registration page](http://127.0.0.1:5000/register).
   The web page should load with a form.
1. Fill in the form with some data, and hit "Register Now".
   You should be redirected to the [home page](http://127.0.0.1:5000/index).
1. Go to [the login page](http://127.0.0.1:5000/login).
   The web page should load with a login form.
1. Fill in the form with the data from earlier, and hit "Login".
   You should be redirected to the [home page](http://127.0.0.1:5000/index).
   You should also see the `Register` and `Login` navigation buttons have disappeared.
1. Go to [the courses page](http://127.0.0.1:5000/courses) and click "Enroll" for a course.
   You should be redirected to the [the enrollment page](http://127.0.0.1:5000/enrollment).
1. Click the `Logout` navigation button and you should be logged out.
