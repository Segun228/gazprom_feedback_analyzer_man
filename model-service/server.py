import json
import os
import pickle
from typing import List

import torch
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from producer import build_message_batch
MODEL_PATH = os.environ.get("SENTIMENT_MODEL_PATH", r"full_path_to_model")
from datetime import datetime, timezone
from datetime import datetime

MODEL_PATH = os.environ.get("SENTIMENT_MODEL_PATH",
                            r"PATH_TO_MODEL")

if torch.backends.mps.is_available():
    device = torch.device("mps")
elif torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")
print("Using device:", device)

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
except Exception as e:
    raise RuntimeError(f"Ошибка при загрузке модели/tokenizer из {MODEL_PATH}: {e}")

with open("sklearn_model.pkl", "rb") as f:
    model_classification = pickle.load(f)
with open("vectorizer.pkl", "rb") as f:
    vectorizer = pickle.load(f)
with open("class_info.json", "r", encoding="utf-8") as f:
    class_info = json.load(f)
    class_names = class_info["class_names"]


def extract_tags(text):
    x_text = vectorizer.transform([text])
    y_pred = model_classification.predict(x_text)
    predicted_labels = []
    for i, class_name in enumerate(class_names):
        if y_pred[0][i] == 1:
            predicted_labels.append(class_name)
    return predicted_labels


def predict_logits(texts: List[str]):
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=256
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
    probs = torch.softmax(logits, dim=1).cpu().numpy()
    preds = torch.argmax(logits, dim=1).cpu().numpy().tolist()
    return preds, probs


app = FastAPI()


class PredictRequest(BaseModel):
    text: str


class TextData(BaseModel):
    id: int
    text: str

class PredictBatchRequest(BaseModel):
    data: List[TextData]


from datetime import datetime

class PredictResponse(BaseModel):
    text: str
    label: int
    probabilities: List[float]
    tags: List[str]

    def get_json_response(self):
        return {
            "text": self.text,
            "sentiment": self.label,
            "date": datetime.now(timezone.utc).isoformat(),
            "tags": self.tags
        }

class PredictionItem(BaseModel):
    id: int
    topics: List[str]
    sentiments: List[str]


class PredictBatchResponse(BaseModel):
    predictions: List[PredictionItem]

def extract_tags(text: str) -> List[str]:
    return [w for w in text.lower().split() if len(w) > 3][:5]

def map_sentiment_to_text(label: int) -> str:
    """Маппинг числового sentiment в текстовый"""
    sentiment_map = {
        0: "отрицательно",
        1: "нейтрально",
        2: "положительно"
    }
    return sentiment_map.get(label, "нейтрально")

def extract_topics(text: str, tags: List[str]) -> List[str]:
    """Извлекаем топики из текста (упрощенная версия)"""
    topics = []
    if any(word in text.lower() for word in ['банк', 'обслуживание', 'сервис']):
        topics.append("Обслуживание")
    if any(word in text.lower() for word in ['приложение', 'мобильн']):
        topics.append("Мобильное приложение")
    if any(word in text.lower() for word in ['карт', 'кредит']):
        topics.append("Кредитная карта")
    
    return topics if topics else ["Общее"]

@app.post("/predict_single", response_model=PredictResponse)
def predict_endpoint(req: PredictRequest, background_tasks: BackgroundTasks):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    preds, probs = predict_logits([req.text])

    prediction = PredictResponse(
        text=req.text,
        label=preds[0],
        probabilities=probs[0].tolist(),
        tags=extract_tags(req.text)
    )
    background_tasks.add_task(build_message_batch, [prediction.get_json_response()])

    build_message_batch([prediction.get_json_response()])
    return prediction


@app.post("/predict", response_model=PredictBatchResponse)
def predict_batch_endpoint(req: PredictBatchRequest):
    if not req.data:
        raise HTTPException(status_code=400, detail="Empty data list")
def predict_batch_endpoint(req: PredictBatchRequest, background_tasks: BackgroundTasks):
    if not req.texts:
        raise HTTPException(status_code=400, detail="Empty texts list")

    texts = [item.text for item in req.data]
    preds, probs = predict_logits(texts)

    kafka_messages = []
    predictions = []
    
    for item, pred, prob in zip(req.data, preds, probs):
        tags = extract_tags(item.text)
        topics = extract_topics(item.text, tags)
        sentiment_text = map_sentiment_to_text(pred)
        
        # Для API ответа (новый формат)
        predictions.append(PredictionItem(
            id=item.id,
            topics=topics,
            sentiments=[sentiment_text]
        ))
        
        # Для Kafka (старый формат)
        kafka_messages.append({
            "text": item.text,
            "sentiment": pred,
            "date": datetime.now(timezone.utc).isoformat(),
            "tags": tags
        })
    
    # Отправляем в Kafka
    build_message_batch(kafka_messages)
    
    return PredictBatchResponse(predictions=predictions)
    results = [
        PredictResponse(
            text=txt,
            label=pred,
            probabilities=prob.tolist(),
            tags=extract_tags(txt)
        )
        for txt, pred, prob in zip(req.texts, preds, probs)
    ]
    response = PredictBatchResponse(results=results)
    background_tasks.add_task(build_message_batch, response.get_list_json_response())
    return response

    results = [
        PredictResponse(
            text=txt,
            label=pred,
            probabilities=prob.tolist(),
            tags=extract_tags(txt)
        )
        for txt, pred, prob in zip(req.texts, preds, probs)
    ]

    response = PredictBatchResponse(results=results)
    build_message_batch(response.get_list_json_response())
    return response

@app.get("/health")
def health():
    return {"status": model.config.num_labels == 3, "device": str(device)}
