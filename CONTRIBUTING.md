# Contributing

## Ubuntu Environment Setup

```bash
# install python 3 and dependencies
sudo apt update
sudo apt install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    hadolint \
    python3 \
    python-dev \
    python3-pip \
    python3-venv

# ensure python 3 is the default python version
cat >> ~/.bashrc << EOF

# python3 alias
alias python=python3
EOF
python --version

# install ruby for markdown linting
sudo apt install ruby
sudo gem install mdl
```

## Clone and Install

```bash
git clone git@github.com:robert-7/Course-Enrollment-App.git
cd Course-Enrollment-App
```

## Virtual Environment

```bash
# set up virtualenv
python -m venv '.venv'
source .venv/bin/activate

# install requirements
pip install -r requirements.txt

# set up pre-commit so basic linting happens before every commit
pre-commit install
pre-commit run --all-files
```

To deactivate or reactivate your virtual environment:

```bash
deactivate                # deactivates virtualenv
source .venv/bin/activate # reactivates virtualenv
```

## MongoDB Shell Access

To hop into the `mongodb` container and inspect the database:

```bash
docker compose exec mongodb mongo NOU_Enrollment
db.getCollectionNames()
db.user.find()
```

## Install Mongo Compass

For a GUI to inspect MongoDB, install [Mongo Compass](https://www.mongodb.com/products/tools/compass).

## Postman

After installing Postman, import [the Postman collection](.postman/collection.json) for the full API setup.
