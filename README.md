# Course Enrollment App

A full-stack Flask web application for course enrollment with user
authentication, MongoDB-backed data models, REST APIs with Swagger docs,
and a fully containerized Docker Compose setup.

## Getting Set Up

Please see [the setup documentation](SETUP.md) regarding this.

## Features to try

Please see [the testing documentation](TESTING.md) that showcases an end-to-end demo of features supported.

## Notes about Files and Folders

Some important files and folders are seen below:

* **application/** — Flask app (routes, models, forms, templates)
* **mongo-setup/** — MongoDB seed data and initialization script
* **Docker Compose** orchestrates the Flask app, MongoDB, and seed containers

## Acknowledgments

This project was originally based on the LinkedIn Learning course
["Full Stack Web Development with Flask"](https://www.linkedin.com/learning/full-stack-web-development-with-flask).
It has since been extended with Docker containerization, CI/CD pipelines,
rebranded course data, and additional tooling.
