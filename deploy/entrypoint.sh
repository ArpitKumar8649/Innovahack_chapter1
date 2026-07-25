#!/bin/sh
# Production entrypoint: nginx edge (:8080) + API (:8000, internal only).
nginx
cd /app/verifact/backend
exec uvicorn main:app --host 127.0.0.1 --port 8000
