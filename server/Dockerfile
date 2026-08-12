FROM mcr.microsoft.com/azure-functions/python:4-python3.11 AS base

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/app

CMD ["python", "-m", "src.ingestion.iot_generator"]
