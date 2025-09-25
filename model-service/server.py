import os
from typing import List

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification

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
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH).to(device)
except Exception as e:
    raise RuntimeError(f"Ошибка при загрузке модели/tokenizer из {MODEL_PATH}: {e}")


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


class PredictBatchRequest(BaseModel):
    texts: List[str]


class PredictResponse(BaseModel):
    text: str
    label: int
    probabilities: List[float]


class PredictBatchResponse(BaseModel):
    results: List[PredictResponse]


@app.post("/predict", response_model=PredictResponse)
def predict_endpoint(req: PredictRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")
    preds, probs = predict_logits([req.text])
    return PredictResponse(text=req.text, label=preds[0], probabilities=probs[0].tolist())


@app.post("/predict_batch", response_model=PredictBatchResponse)
def predict_batch_endpoint(req: PredictBatchRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="Empty texts list")
    preds, probs = predict_logits(req.texts)
    results = [PredictResponse(text=txt, label=pred, probabilities=prob.tolist()) for txt, pred, prob in
               zip(req.texts, preds, probs)]
    return PredictBatchResponse(results=results)


@app.get("/health")
def health():
    return {"status": model.config.num_labels == 3, "device": str(device)}
