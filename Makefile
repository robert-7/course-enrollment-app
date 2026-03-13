.PHONY: run test e2e-demo e2e-fast e2e-docker seed lint clean setup

## Generate .env with a random SECRET_KEY (skips if .env already exists)
setup:
	@if [ -f .env ]; then \
		echo ".env already exists — skipping. Delete it first to regenerate."; \
	else \
		echo "SECRET_KEY=$$(python3 -c 'import secrets; print(secrets.token_hex(32))')" > .env; \
		echo ".env created with a fresh SECRET_KEY."; \
	fi

## Start the app
run:
	docker compose up -d --build

## Run the test suite (requires pytest in requirements.txt)
test:
	docker compose exec course-enrollment-app python -m pytest

## Run end-to-end demo test
e2e-demo:
	npm run e2e:walkthrough:demo

## Run end-to-end walkthrough quickly
e2e-fast:
	npm run e2e:walkthrough:fast

## Run end-to-end walkthrough in Docker (no local npm required)
e2e-docker:
	docker compose run --rm e2e-tests

## Re-seed the database
seed:
	docker compose run --rm mongo-seed

## Run linters via pre-commit
lint:
	pre-commit run --all-files

## Tear down containers and volumes
clean:
	docker compose down -v
