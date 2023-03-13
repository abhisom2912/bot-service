from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder

from models import Protocol, ProtocolUpdate

protocol_router = APIRouter()

@protocol_router.post("/", response_description="Create a new protocol", status_code=status.HTTP_201_CREATED, response_model=Protocol)
def create_protocol(request: Request, protocol: Protocol = Body(...)):
    protocol = jsonable_encoder(protocol)
    if (user := request.app.database["users"].find_one({"_id": protocol['user_id']})) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No user with ID {protocol['user_id']} found")   
    new_protocol = request.app.database["protocols"].insert_one(protocol)
    created_protocol = request.app.database["protocols"].find_one(
        {"_id": new_protocol.inserted_id}
    )

    return created_protocol

@protocol_router.get("/{user_id}", response_description="List all protocols of a particular user", response_model=list[Protocol])
def list_protocols(user_id: str, request: Request):
    protocols = list(request.app.database["protocols"].find({"user_id": user_id}, limit=100))
    return protocols

@protocol_router.get("/{user_id}/{id}", response_description="Get a single protocol by id", response_model=Protocol)
def find_protocol(user_id: str, id: str, request: Request):
    if (protocol := request.app.database["protocols"].find_one({ "$and": [ { "_id": id }, { "user_id": user_id } ] })) is not None:
        return protocol
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with ID {id} not found")

@protocol_router.put("/{user_id}/{id}", response_description="Update protocol details", response_model=Protocol)
def update_protocol(user_id:str, id: str, request: Request, protocol: ProtocolUpdate = Body(...)):
    protocol = {k: v for k, v in protocol.dict().items() if v is not None}
    if len(protocol) >= 1:
        update_result = request.app.database["protocols"].update_one(
            { "$and": [ { "_id": id }, { "user_id": user_id } ] }, {"$set": protocol}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with ID {id} not found")

    if (
        existing_protocol := request.app.database["protocols"].find_one({"_id": id})
    ) is not None:
        return existing_protocol

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with ID {id} not found")

@protocol_router.delete("/{user_id}/{id}", response_description="Delete a protocol")
def delete_protocol(user_id: str, id: str, request: Request, response: Response):
    delete_result = request.app.database["protocols"].delete_one({ "$and": [ { "_id": id }, { "user_id": user_id } ] })

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with ID {id} not found")

