# Backend (FastAPI) image — Team A
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps kept minimal
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# No Alembic revisions are shipped: app.main's lifespan runs init_db() -> create_all
# at boot, so start the API directly. (Keeps the image free of a migration step.)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]