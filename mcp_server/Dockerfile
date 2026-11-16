FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY __init__.py .
COPY config.py .
COPY db.py .
COPY vector_store.py .
COPY ingest_uupdp.py .
COPY init_db.py .
COPY server.py .
COPY migrations/ ./migrations/

EXPOSE 8000

CMD ["sh", "-c", "python init_db.py && python server.py --transport sse"]
