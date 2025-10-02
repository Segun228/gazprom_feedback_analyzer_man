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
RUN pip install --no-cache-dir fastapi==0.110.0 uvicorn[standard]==0.27.1 transformers==4.39.1 pydantic==2.6.3 kafka-python==2.0.2 python-dotenv==1.0.0 scikit-learn==1.7.2
WORKDIR /app
COPY model-service/server.py /app/server.py
COPY model-service/producer.py /app/producer.py
COPY model-service/sentimentmodel /app/sentimentmodel
COPY model-service/sklearn_model.pkl /app/sklearn_model.pkl
COPY model-service/vectorizer.pkl /app/vectorizer.pkl
COPY model-service/class_info.json /app/class_info.json

ENV SENTIMENT_MODEL_PATH=/app/sentimentmodel

EXPOSE 3002

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3002"]
