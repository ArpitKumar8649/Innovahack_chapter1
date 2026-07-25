# ---- Stage 1: build the React + TypeScript frontend ----
FROM node:24-alpine AS web
WORKDIR /web
COPY web/package*.json ./
RUN npm install --silent
COPY web/ ./
RUN npm run build

# ---- Stage 2: runtime (nginx edge + API) ----
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY verifact/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY verifact/ ./verifact/
# nginx serves the built React app and proxies /api to the backend
COPY --from=web /web/dist /usr/share/nginx/html/
COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY deploy/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
