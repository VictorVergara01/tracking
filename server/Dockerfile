# TrackFlow API + web (FastAPI). Build context = ./server
FROM python:3.12-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (main.py, models.py, web/, etc.)
COPY . .

# SQLite database on a mounted volume so it survives rebuilds.
ENV TRACKFLOW_DB_DIR=/data
RUN mkdir -p /data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
