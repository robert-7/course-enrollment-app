# AGENTS.md

## Repo overview

- Maintain a Flask 3.1 course enrollment app backed by MongoDB/MongoEngine.
- Keep the current single-module layout under `application/`: routes, models, forms, templates, and REST API live together.
- Expect local workflows to use Docker Compose; expect automated verification to use pytest, pre-commit, and Playwright.

## Working rules

- Plan before large or multi-file changes. Name the files and behavior you expect to touch.
- Keep diffs small and reviewable. Do not mix feature work with unrelated cleanup.
- Preserve existing patterns unless there is a strong repo-specific reason to change them.
- Avoid unrelated refactors, renames, or module splits unless requested.
- Ask before changing security-sensitive behavior, auth/session handling,
  infra or deployment behavior, database schema or collection names, Docker
  service names, or dependencies.
- Keep secrets out of source control. `SECRET_KEY` must stay env-driven.
- If repo behavior is unclear, write `Unknown / verify before changing` instead of guessing.

## Validation

- For small Python-only changes, run the closest targeted test file, for
  example `pytest tests/test_config.py`, plus
  `pre-commit run --files <changed files>`.
- For route, model, form, or shared behavior changes, run `pytest`.
- For CI-equivalent Python validation, run
  `pytest --cov=application --cov-report=term-missing --cov-fail-under=100`.
- For formatting and linting across the repo, run `pre-commit run --all-files`
  or `make lint`.
- For Docker/local stack verification, use `make setup`, `make run`, and
  `make test`.
- For UI flow, template, routing, auth, or startup changes, also run
  `make e2e-docker` or `docker compose run --rm e2e-tests`.
- Do not claim success without listing the exact commands you ran and whether they passed.

## File-specific guidance

- `application/__init__.py`: App config, CSRF, MongoDB connection, and API
  registration happen at import time. Set env vars before importing
  `application`.
- `config.py`: Only `development`, `testing`, and `production` are supported
  `APP_ENV` values. `production` enables secure session cookies; local HTTP
  flows rely on non-production config.
- `main.py`: Flask entrypoint is intentionally thin. Keep bootstrap logic in
  `application/__init__.py` unless there is a strong reason to move it.
- `application/routes.py`: Web routes and REST API routes live together.
  Preserve session keys (`user_id`, `username`), auth checks, redirects, and
  CSRF-backed form behavior unless the task explicitly changes them.
- `application/models.py`: Model field changes ripple into tests, seed data,
  aggregation logic, and API responses. Treat schema edits as coordinated
  changes.
- `application/course_list.py`: Mongo aggregation depends on current collection
  and field names. Verify compatibility before renaming models or keys.
- `mongo-setup/`: Seed scripts import `user` and `course` data and drop
  `enrollment`. Keep seed data, model fields, and collection expectations
  aligned.
- `tests/conftest.py`: Pytest sets `APP_ENV=testing`, injects `SECRET_KEY` and
  `MONGO_URI`, swaps MongoDB to `mongomock`, and disables CSRF. Preserve this
  isolation when changing bootstrap/config flow.
- `tests/`: `test_models.py`, `test_routes.py`, `test_api.py`, and
  `test_config.py` are the main safety net. Extend the closest existing test
  file when behavior changes.
- `docker-compose.yaml` and `Makefile`: Local service names and commands are
  referenced by docs, CI, and e2e flows. Avoid changing them without approval.
- `docs/aws-architecture.md`: Deployment architecture is documented, but infra
  code is not in this repo. Unknown / verify before changing deployment
  assumptions or release steps.

## PR / completion expectations

- Summarize what changed in repo terms, not just implementation details.
- List the validation you actually ran, with results.
- Call out assumptions, skipped validation, and follow-up work.
- Flag risks explicitly when touching config, auth, schema, Docker, or deployment-related behavior.
