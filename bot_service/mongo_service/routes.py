from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder

from models import Document, DocumentUpdate, Question

document_router = APIRouter()
question_router = APIRouter()

@document_router.post("/", response_description="Create a new document", status_code=status.HTTP_201_CREATED, response_model=Document)
def create_document(request: Request, document: Document = Body(...)):
    document = jsonable_encoder(document)
    new_document = request.app.database["documents"].insert_one(document)
    created_document = request.app.database["documents"].find_one(
        {"_id": new_document.inserted_id}
    )

    return created_document

@document_router.get("/", response_description="List all documents", response_model=list[Document])
def list_documents(request: Request):
    documents = list(request.app.database["documents"].find(limit=100))
    return documents

@document_router.get("/{id}", response_description="Get a single document by id", response_model=Document)
def find_document(id: str, request: Request):
    if (document := request.app.database["documents"].find_one({"_id": id})) is not None:
        return document
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {id} not found")

@document_router.put("/{id}", response_description="Update a document", response_model=Document)
def update_document(id: str, request: Request, document: DocumentUpdate = Body(...)):
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

@document_router.delete("/{id}", response_description="Delete a document")
def delete_document(id: str, request: Request, response: Response):
    delete_result = request.app.database["documents"].delete_one({"_id": id})

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document with ID {id} not found")


@question_router.post("/", response_description="Create a new question", status_code=status.HTTP_201_CREATED, response_model=Question)
def create_question(request: Request, question: Question = Body(...)):
    question = jsonable_encoder(question)
    new_question = request.app.database["questions"].insert_one(question)
    created_question = request.app.database["questions"].find_one(
        {"_id": new_question.inserted_id}
    )

    return created_question

@question_router.get("/", response_description="List all questions", response_model=list[Question])
def list_questions(request: Request):
    questions = list(request.app.database["questions"].find(limit=100))
    return questions


@question_router.get("/{id}", response_description="Get a single question by id", response_model=Question)
def find_question(id: str, request: Request):
    if (question := request.app.database["questions"].find_one({"_id": id})) is not None:
        return question
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Question with ID {id} not found")
