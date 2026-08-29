FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV TELEGRAM_TOKEN="" \
    GEMINI_API_KEY="" \
    BOT_PASSWORD="" \
    ADMIN_ID="0"

CMD ["python", "main.py"]
