FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && ffmpeg -version > /dev/null

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

ENV PYTHONUNBUFFERED=1

WORKDIR /app/src
CMD ["python", "/app/src/bot.py"]
