# Database migrations

Set `DATABASE_URL`, then run `alembic upgrade head` before the backend starts. Production also sets `AUTO_CREATE_TABLES=false`. The same migration supports SQLite and PostgreSQL.

For a new revision after changing SQLAlchemy models, run `alembic revision --autogenerate -m "description"`, inspect the generated operations, then test upgrade and downgrade against a disposable database.
