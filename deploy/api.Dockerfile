FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY api/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY api/app ./app
COPY api/alembic.ini ./alembic.ini
COPY api/alembic ./alembic
RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --create-home appuser \
    && install -d -m 0700 -o appuser -g appuser /var/lib/projectflow-files /var/lib/projectflow-ai
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
