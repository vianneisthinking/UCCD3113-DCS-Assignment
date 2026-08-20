FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AUTO_CREATE_TABLES=false
WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api ./api
COPY migrations ./migrations
COPY alembic.ini docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh && chown -R app:app /app
USER app
EXPOSE 8001
ENTRYPOINT ["./docker-entrypoint.sh"]
