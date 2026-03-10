.PHONY: run test seed lint clean

## Start the app
run:
	docker compose up -d --build

## Run the test suite (requires pytest in requirements.txt)
test:
	docker compose exec flask-app python -m pytest

## Re-seed the database
seed:
	docker compose run --rm mongo-seed

## Run linters via pre-commit
lint:
	pre-commit run --all-files

## Tear down containers and volumes
clean:
	docker compose down -v
