FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 5000

CMD ["python", "server.py"]
