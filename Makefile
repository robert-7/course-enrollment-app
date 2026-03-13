.PHONY: run test e2e-demo e2e-fast e2e-docker seed lint clean

## Start the app
run:
	docker compose up -d --build

## Run the test suite (requires pytest in requirements.txt)
test:
	docker compose exec flask-app python -m pytest

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
