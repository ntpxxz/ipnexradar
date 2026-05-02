FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for scapy
RUN apt-get update && apt-get install -y tcpdump iproute2 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command to run the API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
