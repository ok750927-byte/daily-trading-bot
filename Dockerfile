FROM python:3.11-slim

WORKDIR /app

# Install system deps for common Python packages
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Install optional runtime deps for webhook API
RUN pip install --no-cache-dir fastapi uvicorn

COPY . /app

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "src.trading.webhook_api:app", "--host", "0.0.0.0", "--port", "8000"]
