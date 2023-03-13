from fastapi import FastAPI
from models import DataIn
from utilities import *
import validators
app = FastAPI()



@app.post("/data")
async def root(data: DataIn):
    print(data.data)
    if 'gitbook' in data.data.keys():
        if validators.url(data.data['gitbook']):
            print(data.data['gitbook'])
            gitbook_data_type = "whitepaper"
            outputs, df, document_embeddings = get_data_from_gitbook(gitbook_data_type, data.data['gitbook'])
        else:
            print("Empty or invalid GitBook link")
    if 'github' in data.data.keys():
        if validators.url(data.data['github']) and 'github' in data.data['github']:
            print(data.data['github'])
            outputs, df, document_embeddings = read_from_github(data.title, data.data['github'])
        else:
            print("Empty or invalid GitHub link")
    return {"hello"}
