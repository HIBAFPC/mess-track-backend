# Mess Track Backend

Foundation for the Mess Track SaaS project.

## Tech Stack
- Django 6.0+
- Django REST Framework
- PostgreSQL (psycopg2-binary)
- uv (Package Manager)
- Ruff (Linting & Formatting)
- Pytest (Testing)

## Setup Instructions

### 1. Prerequisites
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) installed

### 2. Environment Setup
Clone the repository and run:
```bash
uv sync
```

### 3. Configuration
Copy `.env.example` to `.env` and update the values:
```bash
cp .env.example .env
```

### 4. Database Migrations
```bash
uv run python manage.py migrate
```

### 5. Running the Development Server
```bash
uv run python manage.py runserver
```

### 6. API Documentation
- Swagger UI: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- Redoc: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)
- Schema: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

## Development Commands

### Running Tests
```bash
uv run pytest
```

### Linting & Formatting
```bash
uv run ruff check .
uv run ruff format .
```

### Pre-commit
```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
