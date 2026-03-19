FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /srv/app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
COPY migrations ./migrations

RUN pip install --upgrade pip && pip install -e .[dev]

COPY . .

CMD ["bash", "-lc", "python -m scripts.wait_for_db && flask --app app:create_app db upgrade && python -m scripts.seed_demo && flask --app app:create_app run --host 0.0.0.0 --port 8000"]
