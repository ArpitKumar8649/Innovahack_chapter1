FROM python:3.12-slim

WORKDIR /app

COPY verifact/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY verifact/ ./verifact/

WORKDIR /app/verifact/backend
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
