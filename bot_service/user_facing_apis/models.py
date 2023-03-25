import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class User(BaseModel):
    user_id: str = Field(default_factory=uuid.uuid4, alias="_id")
    email: EmailStr

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "user_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "email": "xyz@domain.com",
            }
        }


class UserUpdate(BaseModel):
    email: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "email": "abc@domain.com"
            }
        }


class Protocol(BaseModel):
    protocol_id: str = Field(default_factory=uuid.uuid4, alias="_id")
    user_id: str = Field(...)
    protocol_name: str = Field(...)
    protocol_description: str = Field(
        default={"discord_token": "", "telegram_token": ""}, title="The description of the data", max_length=300
    )
    servers: dict or None = Field(default={})
    doc_links: dict or None = Field(default={})
    credits: float = Field(default=0)
    usage: float = Field(default=0)
    default_answer: str = Field(default="I don't know. Please check with admin.")
    questions: list = Field(default={})

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "protocol_id": "057gh609-b04a-5v54-b46c-32537c7c2c6e",
                "user_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "protocol_name": "Router Protocol",
                "protocol_description": "A cross-chain communication infra",
                "servers": {
                    "discord": "1085331583558488104",
                    "telegram": ""
                },
                "doc_links": {"github": [{"url": "https://github.com/router-protocol/router-chain-docs",
                                          "doc_link": "https://devnet-docs.routerprotocol.com/",
                                          "directory": "docs"}, {"url": "xby", "doc_link": "abc", "directory": "docs"}],
                              "gitbook": [{"url": "abc"}, {"url": "xby"}]},
                "credits": 100.45,
                "usage": 0.34,
                "default_answer": "Please ask admin",
                "questions": [{
                    "question": "",
                    "answer": "",
                    "embedding": "",
                    "usage": "",
                    "frequency": ""
                }]
            }
        }


class ProtocolUpdate(BaseModel):
    protocol_name: Optional[str]
    protocol_description: Optional[str]
    servers: Optional[dict]
    doc_links: Optional[dict]
    credits: Optional[float]
    usage: Optional[float]
    default_answer: Optional[str]
    questions: Optional[dict]

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "protocol_name": "Dfyn Exchange",
                "protocol_description": "Decentralized Exchange",
                "servers": {
                    "discord": "1085331583558488104",
                    "telegram": ""
                },
                "doc_links": {"github": [{"url": "https://github.com/router-protocol/router-chain-docs",
                                          "doc_link": "https://devnet-docs.routerprotocol.com/",
                                          "directory": "docs"}, {"url": "xby", "doc_link": "abc", "directory": "docs"}],
                              "gitbook": [{"url": "abc"}, {"url": "xby"}]},
                "credits": 10.45,
                "usage": 8.97,
                "default_answer": "Please ask admin",
                "questions": {
                    "question": "",
                    "answer": "",
                    "embedding": "",
                    "usage": "",
                    "frequency": ""
                }
            }
        }


class Data(BaseModel):
    data_id: str = Field(default_factory=uuid.uuid4, alias="_id")
    protocol_id: str = Field(...)
    data: list = Field(...)
    embeddings: dict = Field(...)
    embeddings_cost: float = Field(default=0)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "data_id": "083jj669-s05c-4v63-b46c-98564c7c2c6e",
                "protocol_id": "057gh609-b04a-5v54-b46c-32537c7c2c6e",
                "data": [],
                "embeddings": {},
                "embeddings_cost": 0.00
            }
        }


class DataUpdate(BaseModel):
    data: Optional[list]
    embeddings: Optional[dict]
    embeddings_cost: Optional[float]

    class Config:
        schema_extra = {
            "example": {
                "data": [],
                "embeddings": {},
                "embeddings_cost": 0.01
            }
        }


class DataFromUser(BaseModel):
    data_id: str = Field(default_factory=uuid.uuid4, alias="_id")
    data: dict = Field(...)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "data_id": "083jj669-s05c-4v63-b46c-98564c7c2c6e",
                "data": {},
            }
        }


class DataFromUserUpdate(BaseModel):
    data: dict = Field(...)
    append: bool = Field(default=True)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "data": {},
                "append": True,
            }
        }
