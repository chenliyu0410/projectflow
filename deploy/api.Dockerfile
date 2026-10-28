FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY api/requirements.lock api/requirements-ocr.lock ./
RUN pip install --no-cache-dir -r requirements.lock
# OCR is optional: opencv needs libGL/glib on slim images. Models are mounted at runtime, never baked in.
# rapidocr-onnxruntime 1.4.4 declares Python <3.13 but runs on 3.13 (verified); pip enforces that cap, uv does not.
ARG WITH_OCR=false
RUN if [ "$WITH_OCR" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
      && rm -rf /var/lib/apt/lists/* \
      && pip install --no-cache-dir --ignore-requires-python -r requirements-ocr.lock; \
    fi
COPY api/app ./app
COPY api/alembic.ini ./alembic.ini
COPY api/alembic ./alembic
RUN groupadd --gid 10001 appuser && useradd --uid 10001 --gid 10001 --create-home appuser \
    && install -d -m 0700 -o appuser -g appuser /var/lib/projectflow-files /var/lib/projectflow-ai
USER appuser
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
