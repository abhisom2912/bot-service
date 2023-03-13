from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder
from utilities.fetch_data import *
from utilities.utility_functions import *
from models import DataFromUser, Data, DataUpdate
import validators

data_router = APIRouter()

@data_router.post("/user_data/{user_id}/{protocol_id}", response_description="Create data for a protocol", status_code=status.HTTP_201_CREATED, response_model=Data)
def create_data(user_id: str, protocol_id: str, request: Request, data: DataFromUser = Body(...)):
    protocol = request.app.database["protocols"].find_one({ "$and": [ { "_id": protocol_id }, { "user_id": user_id } ] })
    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No protocol with user ID {user_id} and protocol ID {protocol_id} found")    
    outputs = []
    document_embeddings = {}
    print(data.data)
    if 'gitbook' in data.data.keys():
        if validators.url(data.data['gitbook']):
            print(data.data['gitbook'])
            gitbook_data_type = "whitepaper"
            outputs, document_embeddings = get_data_from_gitbook(gitbook_data_type, data.data['gitbook'])
        else:
            print("Empty or invalid GitBook link")
    if 'github' in data.data.keys():
        if validators.url(data.data['github']) and 'github' in data.data['github']:
            print(data.data['github'])
            if len(outputs) == 0:
                outputs, document_embeddings = read_from_github(protocol['protocol_name'], data.data['github']) 
            else:
                github_outputs, github_document_embeddings = read_from_github(protocol['protocol_name'], data.data['github']) 
                # append the new output to the outputs in the database
                outputs.extend(github_outputs)
                # append the new embedding to the embedding in the database
                embeddings.update(github_document_embeddings)
        else:
            print("Empty or invalid GitHub link")

    if len(outputs) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"A valid Gitbook or GitHub link has not been provided")    
    else:
        print("came till here")
        data_to_post = {"protocol_id": protocol_id, "data": outputs, "embeddings": untuplify_dict_keys(document_embeddings)}
        created_data = add_data(data_to_post)
    return created_data

@data_router.post("/curated_data", response_description="Add data for a protocol", status_code=status.HTTP_201_CREATED, response_model=Data)
def add_data(request: Request, data: Data = Body(...)):
    # make it so that users cannot access this, only for internal calls
    data = jsonable_encoder(data)
    if (protocol := request.app.database["protocols"].find_one({"_id": data['protocol_id']})) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No protocol with ID {data['protocol_id']} found")       
    new_data = request.app.database["data"].insert_one(data)
    created_data = request.app.database["data"].find_one(
        {"_id": new_data.inserted_id}
    )

    return created_data

@data_router.get("/{id}", response_description="Get data by id", response_model=Data)
def find_data(id: str, request: Request):
    if (data := request.app.database["data"].find_one({"_id": id})) is not None:
        return data
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with ID {id} not found")

@data_router.put("/{id}", response_description="Update data", response_model=Data)
def update_data(id: str, request: Request, data: DataUpdate = Body(...)):
    data = {k: v for k, v in data.dict().items() if v is not None}
    if len(data) >= 1:
        update_result = request.app.database["data"].update_one(
            {"_id": id}, {"$set": data}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with ID {id} not found")

    if (
        existing_data := request.app.database["data"].find_one({"_id": id})
    ) is not None:
        return existing_data

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with ID {id} not found")

@data_router.delete("/{id}", response_description="Delete data")
def delete_data(id: str, request: Request, response: Response):
    delete_result = request.app.database["data"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with ID {id} not found")
