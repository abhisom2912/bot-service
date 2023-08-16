from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder

from models import Document, DocumentUpdate

document_router = APIRouter()

# API endpoint to create a new document
# response type is "Document" as defined in the models.py file
@document_router.post("/", response_description="Create a new document", status_code=status.HTTP_201_CREATED, response_model=Document)
def create_document(request: Request, document: Document = Body(...)):
    document = jsonable_encoder(document)
    if request.app.database["documents"].find_one( {"$and": [ { "protocol_title": document['protocol_title'] }, {"document_type": document['document_type']}] }):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"This protocol and document type already exists")
    new_document = request.app.database["documents"].insert_one(document)
    created_document = request.app.database["documents"].find_one(
        {"_id": new_document.inserted_id}
    )

    return created_document

# API endpoint to list all the documents in the database
@document_router.get("/", response_description="List all documents", response_model=list[Document])
def list_documents(request: Request):
    documents = list(request.app.database["documents"].find(limit=100))
    return documents

# API endpoint to return a specific document
@document_router.get("/{id}", response_description="Get a single document by id", response_model=Document)
def find_document(id: str, request: Request):
    if (document := request.app.database["documents"].find_one({"_id": id})) is not None:
        return document
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {id} not found")

# API endpoint to update a specific document via its protocol title and document type 
@document_router.put("/{protocol_title}/{document_type}", response_description="Update a document", response_model=Document)
def update_document(protocol_title: str, document_type: str, request: Request, document: DocumentUpdate = Body(...)):
    document = {k: v for k, v in document.dict().items() if v is not None}
    if len(document) >= 1:
        update_result = request.app.database["documents"].update_one(
            { "$and": [ { "protocol_title": protocol_title }, { "document_type": document_type } ] }, {"$set": document}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {id} not found")

    if (
        existing_document := request.app.database["documents"].find_one({ "$and": [ { "protocol_title": protocol_title }, { "document_type": document_type } ] })
    ) is not None:
        return existing_document

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {id} not found")

# API endpoint to update a specific document via its id
@document_router.put("/{id}", response_description="Update a document", response_model=Document)
def update_document_via_id(id: str, request: Request, document: DocumentUpdate = Body(...)):
    document = {k: v for k, v in document.dict().items() if v is not None}
    if len(document) >= 1:
        update_result = request.app.database["documents"].update_one(
            {"_id": id}, {"$set": document}
        )

        if update_result.modified_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {id} not found")

    if (
        existing_document := request.app.database["documents"].find_one({"_id": id})
    ) is not None:
        return existing_document

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {id} not found")


# API endpoint to delete a specific document via its protocol title and document type
@document_router.delete("/{protocol_title}/{document_type}", response_description="Delete a document")
def delete_document(protocol_title: str, document_type: str, request: Request, response: Response):
    delete_result = request.app.database["documents"].delete_one({ "$and": [ { "protocol_title": protocol_title }, { "document_type": document_type } ] })

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document for {protocol_title} and {document_type} not found")

# API endpoint to delete a specific document via its id
@document_router.delete("/{id}", response_description="Delete a document")
def delete_document_via_id(id: str, request: Request, response: Response):
    delete_result = request.app.database["documents"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {id} not found")
