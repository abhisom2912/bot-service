from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder
from datetime import datetime

from models import Protocol, ProtocolUpdate
import uuid

protocol_router = APIRouter()


@protocol_router.post("/", response_description="Create a new protocol", status_code=status.HTTP_201_CREATED,
                      response_model=Protocol)
def create_protocol(request: Request, protocol: Protocol = Body(...)):
    protocol = jsonable_encoder(protocol)
    if (user := request.app.database["users"].find_one({"_id": protocol['user_id']})) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No user with ID {protocol['user_id']} found")
    new_protocol = request.app.database["protocols"].insert_one(protocol)
    created_protocol = request.app.database["protocols"].find_one(
        {"_id": new_protocol.inserted_id}
    )

    return created_protocol


@protocol_router.get("/getProtocolByUser/{user_id}", response_description="List all protocols of a particular user",
                     response_model=list[Protocol])
def list_protocols(user_id: str, request: Request):
    protocols = list(request.app.database["protocols"].find({"user_id": user_id}, limit=100))
    return protocols


@protocol_router.get("/getAllProtocols", response_description="List all protocols", response_model=list[Protocol])
def list_all_protocols(request: Request):
    protocols = list(request.app.database["protocols"].find())
    return protocols


@protocol_router.get("/{user_id}/{id}", response_description="Get a single protocol by id", response_model=Protocol)
def find_protocol(user_id: str, id: str, request: Request):
    if (
    protocol := request.app.database["protocols"].find_one({"$and": [{"_id": id}, {"user_id": user_id}]})) is not None:
        return protocol
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with ID {id} not found")


@protocol_router.put("/{user_id}/{id}", response_description="Update protocol details", response_model=Protocol)
def update_protocol(user_id: str, id: str, request: Request, protocol: ProtocolUpdate = Body(...)):
    protocol = {k: v for k, v in protocol.dict().items() if v is not None}
    if len(protocol) >= 1:
        update_result = request.app.database["protocols"].update_one(
            {"$and": [{"_id": id}, {"user_id": user_id}]}, {"$set": protocol}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with ID {id} not found")

    if (
            existing_protocol := request.app.database["protocols"].find_one({"_id": id})
    ) is not None:
        return existing_protocol

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with ID {id} not found")


@protocol_router.put("/addResponse", response_description="Update mod responses")
def add_mod_response(request: Request, server_type: str=Body(...), server_id: str=Body(...), question: str=Body(...), response: str=Body(...)):
    search_key = 'servers.' + server_type + '.server'
    protocol = request.app.database["protocols"].find_one({search_key: server_id})

    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Protocol for {server_type} with server id - {server_id} not found")

    mod_response = {'id': str(uuid.uuid4()), 'question': question, 'answer': response, 'server': server_type, 'added_time': datetime.now(),
                    'is_trained': False, 'train_time': datetime(9999, 12, 31)}
    protocol['mod_responses'].append(mod_response)
    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol['_id']}, {"$set": protocol}
    )


@protocol_router.delete("/{user_id}/{id}", response_description="Delete a protocol")
def delete_protocol(user_id: str, id: str, request: Request, response: Response):
    protocol = request.app.database["protocols"].find_one({"$and": [{"_id": id}, {"user_id": user_id}]})
    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Protocol with ID {id} not found")
    protocol['active'] = False
    update_result = request.app.database["protocols"].update_one(
        {"$and": [{"_id": id}, {"user_id": user_id}]}, {"$set": protocol}
    )
    return protocol

