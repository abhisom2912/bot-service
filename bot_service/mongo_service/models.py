import uuid
from typing import Optional
from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    description: str = Field(...)
    data: list = Field(...)
    embeddings: dict = Field(...)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "description": "Router Protocol voyager",
                "data": [],
                "embeddings": {}
            }
        }

class DocumentUpdate(BaseModel):
    description: Optional[str]
    data: Optional[list]
    embeddings: Optional[dict]

    class Config:
        schema_extra = {
            "example": {
                "description": "Router Protocol relayer",
                "data": [],
                "embeddings": {}
            }
        }

class Question(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    bot_id: str = Field(...)
    question: str = Field(...)
    answer: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "bot_id": "1",
                "question": "what is xyz?",
                "answer": "xyz is abc"
            }
        }