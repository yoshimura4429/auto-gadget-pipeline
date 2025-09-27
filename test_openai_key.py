import os, requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENAI_API_KEY")
print("KEY loaded:", bool(key), "len:", len(key) if key else 0)

url = "https://api.openai.com/v1/models"
headers = {"Authorization": f"Bearer {key}"}
try:
    r = requests.get(url, headers=headers, timeout=30)
    print("HTTP:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        names = [m["id"] for m in data.get("data", [])[:5]]
        print("Models sample:", names)
    else:
        print("Body:", r.text[:400])
except Exception as e:
    print("ERROR:", type(e).__name__, e)
