# VeritasAI — production image: nginx edge + API in one container.
# nginx serves the frontend on :8080 and proxies /api/* to uvicorn on :8000.
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY verifact/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY verifact/ ./verifact/
COPY verifact/frontend/ /usr/share/nginx/html/
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
