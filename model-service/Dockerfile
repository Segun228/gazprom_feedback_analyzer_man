FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Обновим pip
RUN pip install --no-cache-dir --upgrade pip

# Устанавливаем torch только CPU (фиксированная версия)
RUN pip install --no-cache-dir torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu

# Остальные зависимости
RUN pip install --no-cache-dir "numpy<2"
RUN pip install --no-cache-dir fastapi==0.110.0 uvicorn[standard]==0.27.1 transformers==4.39.1 pydantic==2.6.3
WORKDIR /app
COPY server.py /app/server.py
COPY sentimentmodel /app/sentimentmodel

ENV SENTIMENT_MODEL_PATH=/app/sentimentmodel

EXPOSE 3002

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3002"]
