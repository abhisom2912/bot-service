import openai
import requests
import os
import json

OPENAI_ENGINE_ID = os.getenv('OPENAI_ENGINE_ID')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def main():
    print('testing_123')
    url = "https://api.openai.com/v1/engines/" + OPENAI_ENGINE_ID + "/completions"
    data = '{"prompt": "Write python code for saying hello!", "max_tokens": 500, "temperature": 0, "stop": "//", "n": 1}'
    headers = {
        'Authorization': "Bearer " + OPENAI_API_KEY,
        'Accept': "application/json",
        'Content-Type': "application/json",
        'Cache-Control': "no-cache",
        'Postman-Token': "e334c267-0fe1-ee39-2234-fd3519851b49"
    }

    r = requests.post(url, data=data, headers=headers)
    final_answer = json.loads(r.content.decode("utf-8").replace("'", '"'))['choices'][0]

if __name__ == '__main__':
    main()