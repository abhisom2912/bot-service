import uuid
from typing import Optional
from pydantic import BaseModel, Field

class Document(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, alias="_id")
    protocol_title: str = Field(...)
    document_type: str = Field(...)
    data: list = Field(...)
    embeddings: dict = Field(...)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "protocol_title": "Router",
                "document_type" : "Github",
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
