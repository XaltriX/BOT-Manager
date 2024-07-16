FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot_script.py .
COPY bot_tokens.txt .

CMD ["python", "bot.py"]
