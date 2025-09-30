import os
from typing import List

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from producer import build_message_batch
MODEL_PATH = os.environ.get("SENTIMENT_MODEL_PATH", r"full_path_to_model")
from datetime import datetime


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
            "date": datetime.now().isoformat(),
            "tags": self.tags
        }


class PredictBatchResponse(BaseModel):
    results: List[PredictResponse]

    def get_list_json_response(self):
        return [r.get_json_response() for r in self.results]


def extract_tags(text: str) -> List[str]:
    return [w for w in text.lower().split() if len(w) > 3][:5]


@app.post("/predict_single", response_model=PredictResponse)
def predict_endpoint(req: PredictRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Empty text")

    preds, probs = predict_logits([req.text])

    prediction = PredictResponse(
        text=req.text,
        label=preds[0],
        probabilities=probs[0].tolist(),
        tags=extract_tags(req.text)
    )

    build_message_batch([prediction.get_json_response()])
    return prediction


@app.post("/predict", response_model=PredictBatchResponse)
def predict_batch_endpoint(req: PredictBatchRequest):
    if not req.texts:
        raise HTTPException(status_code=400, detail="Empty texts list")

    preds, probs = predict_logits(req.texts)

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
#
# Text: Очень доволен приложением банка
# Class: 2
# Probabilities: [0.03496845066547394, 0.15588398277759552, 0.8091475367546082]
# Text: Очень доволен приложением банка
# Class: 2
# Probabilities: [0.03496844694018364, 0.15588392317295074, 0.8091475963592529]
# Text: Приложение виснет, поддержка ужас
# Class: 0
# Probabilities: [0.6237407326698303, 0.3564715087413788, 0.019787730649113655]
# Text: Обычный опыт, ничего особенного
# Class: 2
# Probabilities: [0.007893973030149937, 0.4094514548778534, 0.5826546549797058]
