import requests
import json

BASE_API_URL = "http://127.0.0.1:8000/document/"

response = requests.get(BASE_API_URL)
answer = response.json()
print(answer[0]['data'])