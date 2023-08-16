import uuid
from typing import Optional
from pydantic import BaseModel, Field

# note, here we refer to any data type that is added as a "document" - for eg. Gitbook docs, PDF document, Medium article, among others
# you can upload multiple documents


# schema of a document (this is the format in which Mongo will store the record while creating a document)
class Document(BaseModel):
    id: str = Field(default_factory=uuid.uuid4, alias="_id") # auto-generated, don't need to pass this while creating a document
    protocol_title: str = Field(...) # title of your protocol
    document_type: str = Field(...) # Gitbook, PDF, Medium article, etc.
    data: list = Field(...) # relevant data picked up from your Gitbook/Notion/PDF/Docusaurus
    embeddings: dict = Field(...)  # embeddings against the data (these allow us to match user's queries against the data present in your document)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "protocol_title": "Router Protocol",
                "document_type" : "Gitbook",
                "data": [],
                "embeddings": {}
            }
        }

# this is the format in which the data needs to be passed while updating a document
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
