FROM python:3.12-slim
WORKDIR /app
COPY requisitos.txt .
RUN pip install --no-cache-dir -r requisitos.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} app:app"]
