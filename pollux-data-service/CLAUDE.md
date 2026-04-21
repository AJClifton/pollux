# Project Context

When working with this codebase, prioritize readability over cleverness. Ask clarifying questions before making architectural changes.

## About This Project

Flask REST API for fetching forecast data from a Redis cache, database, or API. Uses SQLAlchemy for database operations to a PostgreSQL database. Gunicorn will be used for deployment and the app will be containerised.

## Key Directories

- `app/models/` - database models
- `app/api/` - route handlers
- `app/core/` - configuration and utilities

## Standards

- do not use '__init__.py' files unless absolutely required 
- pytest for testing (fixtures in `tests/conftest.py`)
- pytest tests should be written with Arrange Act Assert comments with the name format function_input_expectedResult()
- PEP 8 with 100 character lines
- import statements should be at the top of the file, not in functions

## Common Commands
```bash
python -m flask --app {name} run    # dev server
python -m pytest tests/ -v          # run tests
```

# Workflow
- Run tests after making changes, run all the tests that refer to modified functions.

## Notes