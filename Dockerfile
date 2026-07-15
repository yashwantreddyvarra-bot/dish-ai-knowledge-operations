FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium

COPY . .
RUN mkdir -p output/docs output/videos output/screenshots output/vframes output/vector_db

ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV CAPTURE_HEADLESS=1
EXPOSE 5000

CMD ["python", "server.py"]
