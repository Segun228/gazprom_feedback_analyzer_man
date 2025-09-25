import requests

BASE_URL = "http://localhost:3002"
single_example = {"text": "Очень доволен приложением банка"}

resp = requests.post(f"{BASE_URL}/predict", json=single_example)
if resp.status_code == 200:
    data = resp.json()
    print("Text:", data["text"])
    print("Class:", data["label"])
    print("Probabilities:", data["probabilities"])
else:
    print("Error: ", resp.text)

batch_example = {
    "texts": [
        "Очень доволен приложением банка",
        "Приложение виснет, поддержка ужас",
        "Обычный опыт, ничего особенного"
    ]
}

resp = requests.post(f"{BASE_URL}/predict_batch", json=batch_example)
if resp.status_code == 200:
    data = resp.json()
    for elem in data["results"]:
        print(f"Text: {elem['text']}")
        print(f"Class: {elem['label']}")
        print(f"Probabilities: {elem['probabilities']}")
else:
    print("Error:", resp.text)
