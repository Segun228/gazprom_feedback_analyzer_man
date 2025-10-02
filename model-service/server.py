import json
import os
import pickle
from typing import List

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from producer import build_message_batch
from datetime import datetime, timezone

MODEL_PATH = os.environ.get("SENTIMENT_MODEL_PATH", r"full_path_to_model")

if torch.backends.mps.is_available():
    device = torch.device("mps")
elif torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")
print("Using device:", device)

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    sentiment_model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
    print("Sentiment model loaded successfully")
except Exception as e:
    raise RuntimeError(f"Ошибка при загрузке sentiment модели/tokenizer из {MODEL_PATH}: {e}")

try:
    with open('/app/sklearn_model.pkl', 'rb') as f:
        topic_model = pickle.load(f)
    with open('/app/vectorizer.pkl', 'rb') as f:
        vectorizer = pickle.load(f)
    with open('/app/class_info.json', 'r', encoding='utf-8') as f:
        class_info = json.load(f)
        topic_class_names = class_info['class_names']
    print(f"Topic model loaded successfully with {len(topic_class_names)} classes: {topic_class_names}")
except Exception as e:
    print(f"Ошибка при загрузке topic модели: {e}")
    topic_model = None
    vectorizer = None
    topic_class_names = []


def predict_sentiment(texts: List[str]):
    """Predict sentiment using transformer model"""
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=256
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = sentiment_model(**inputs)
        logits = outputs.logits
    probs = torch.softmax(logits, dim=1).cpu().numpy()
    preds = torch.argmax(logits, dim=1).cpu().numpy().tolist()
    return preds, probs


def predict_topics(texts: List[str]) -> List[List[str]]:
    """Predict topics using sklearn multi-label model"""
    if topic_model is None or vectorizer is None:
        return [["другое"] for _ in texts]
    
    try:
        X = vectorizer.transform(texts)
        
        y_pred = topic_model.predict(X)
        
        results = []
        for pred_row in y_pred:
            topics = [topic_class_names[i] for i, val in enumerate(pred_row) if val == 1]
            results.append(topics if topics else ["другое"])
        
        return results
    except Exception as e:
        print(f"Error predicting topics: {e}")
        return [["другое"] for _ in texts]


def map_sentiment_to_text(label: int) -> str:
    """Маппинг числового sentiment в текстовый"""
    sentiment_map = {
        0: "отрицательно",
        1: "нейтрально",
        2: "положительно"
    }
    return sentiment_map.get(label, "нейтрально")


app = FastAPI()


class PredictRequest(BaseModel):
    text: str


class TextData(BaseModel):
    id: int
    text: str


class PredictBatchRequest(BaseModel):
    data: List[TextData]


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


@app.post("/predict_single", response_model=PredictResponse)
def predict_endpoint(req: PredictRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    preds, probs = predict_sentiment([req.text])
    topics = predict_topics([req.text])[0]

    prediction = PredictResponse(
        text=req.text,
        label=preds[0],
        probabilities=probs[0].tolist(),
        tags=topics 
    )

    build_message_batch([prediction.get_json_response()])
    return prediction


@app.post("/predict", response_model=PredictBatchResponse)
def predict_batch_endpoint(req: PredictBatchRequest):
    if not req.data:
        raise HTTPException(status_code=400, detail="Empty data list")

    texts = [item.text for item in req.data]
    
    sentiment_preds, sentiment_probs = predict_sentiment(texts)
    
    topics_batch = predict_topics(texts)

    kafka_messages = []
    predictions = []
    
    for item, sent_pred, sent_prob, topics in zip(req.data, sentiment_preds, sentiment_probs, topics_batch):
        sentiment_text = map_sentiment_to_text(sent_pred)
        sentiments_per_topic = [sentiment_text] * len(topics)
        
        predictions.append(PredictionItem(
            id=item.id,
            topics=topics,
            sentiments=sentiments_per_topic
        ))
        
        kafka_messages.append({
            "text": item.text,
            "sentiment": sent_pred,
            "date": datetime.now(timezone.utc).isoformat(),
            "tags": topics
        })
    
    build_message_batch(kafka_messages)
    
    return PredictBatchResponse(predictions=predictions)


@app.get("/health")
def health():
    return {
        "status": sentiment_model.config.num_labels == 3,
        "device": str(device),
        "topic_model_loaded": topic_model is not None,
        "num_topic_classes": len(topic_class_names) if topic_class_names else 0,
        "topic_classes": topic_class_names
    }
