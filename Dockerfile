FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    whois curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_domain_check.py .

EXPOSE 8083

CMD ["python", "mcp_domain_check.py"]
