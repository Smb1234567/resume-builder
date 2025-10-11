import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

def list_free_models():
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    free_models = [
        m for m in data.get("data", [])
        if ":free" in m.get("id", "").lower()
        or (m.get("pricing", {}).get("prompt", 1) == 0)
    ]

    print(f"[INFO] ✅ Found {len(free_models)} free models:\n")
    for model in free_models:
        print(f"🧠 {model.get('name')} | ID: {model.get('id')}")

if __name__ == "__main__":
    list_free_models()

