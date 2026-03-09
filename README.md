# Course Enrollment App

A full-stack Flask web application for course enrollment with user
authentication, MongoDB-backed data models, REST APIs with Swagger docs,
and a fully containerized Docker Compose setup.

## Getting Set Up

Please see [the setup documentation](SETUP.md) regarding this.

## Features to try

* You should be able to register a user. This can be done from the `/register` path.
* You should be able to login as a user after registering. This can be done from the
  `/login` path.

## Folder and File Structure

* [.github/workflows](.github/workflows) - Holds the GitHub Actions files that enables
  CI/CD software workflows
* [.postman](.postman) - Holds files related to Postman setup for API testing
* [.vscode](.vscode) - Holds the Visual Studio Code settings for this project
* [application](application) - Holds the application specific code for this project
* [mongo-setup](mongo-setup) - Holds the files needed to populate our MongoDB instance
* [.flake8](.flake8) - Configuration file for the flake8 Python linter
* [.flaskenv](.flaskenv) - Defines some parameters that Flask needs to run
* [.gitignore](.gitignore) - Defines the files/folders to ignore in this repository
* [.markdownlint.rb](.markdownlint.rb) - Configuration file for the pre-commit markdown
  linter
* [.markdownlint.yaml](.markdownlint.rb) - Configuration file for the GitHub Actions
  markdown linter
* [.pre-commit-config.yaml](.pre-commit-config.yaml) - Defines the linting plugins that
  run before any commit. See [SETUP.md](SETUP.md)
* [config.py](config.py) - Defines the configurations for the server
* [LICENSE](LICENSE) - Licensing file
* [main.py](main.py) - Calls the application's entrypoint
* [requirements.txt](requirements.txt) - Pip package requirements for enabling
  developers to contribute. See [SETUP.md](SETUP.md)
* [SETUP.md](SETUP.md) - Setup instructions for contributors
* [TESTING.md](TESTING.md) - Instructions for manually validating the website functionality works.

## Acknowledgments

This project was originally based on the LinkedIn Learning course
["Full Stack Web Development with Flask"](https://www.linkedin.com/learning/full-stack-web-development-with-flask).
It has since been extended with Docker containerization, CI/CD pipelines,
rebranded course data, and additional tooling.
