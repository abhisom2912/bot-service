import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# schema to follow while saving details of an interested user
class ContactUs(BaseModel):
    contactus_id: str = Field(default_factory=uuid.uuid4, alias="_id")
    name: str = Field(default="Name unknown")
    email: EmailStr
    message: str = Field(...)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "contactus_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "name": "John Doe",
                "email": "xyz@domain.com",
                "message": "I want to integrate scarlett"
            }
        }

# schema to follow while adding a registered user
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

# schema to follow while updating the details of a registered user
class UserUpdate(BaseModel):
    email: Optional[str]

    class Config:
        schema_extra = {
            "example": {
                "email": "abc@domain.com"
            }
        }

# schema to follow while the details of a questioner (to enforce rate limit and prevent any questioner from abusing the system)
class Questioner(BaseModel):
    questioner_id: str = Field(..., alias="_id")
    server_type: str = Field(...)
    questioner_server_id: str = Field(...)
    user_protocol_limits: dict or None = Field(default={})
    questions: list = Field(default={})

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "questioner_id": "057gh609-b04a-5v54-b46c-32537c7c2c6e",
                "server_type": "discord",
                "questioner_server_id": "12467",
                "user_protocol_limits": {
                    "066de609-b04a-4b30-b46c-32537c7f1f6e": {
                        "first_question_time": "",
                        "questions_asked": 2
                    }
                },
                "questions": {
                    "066de609-b04a-4b30-b46c-32537c7f1f6e": [
                        "What is xyz protocol?"
                    ]
                }
            }
        }

# schema to follow while updating the details of a questioner
class QuestionerUpdate(BaseModel):
    server_type: Optional[str]
    questioner_server_id: Optional[str]
    user_protocol_limits: Optional[dict]
    questions: Optional[dict]

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "server_type": "discord",
                "questioner_server_id": "12467",
                "user_protocol_limits": {
                    "protocol_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                    "first_question_time": "",
                    "questions_asked": 2
                },
                "questions": {
                    "question": "What is xyz protocol?",
                    "protocol_id": "066de609-b04a-4b30-b46c-32537c7f1f6e"
                }
            }
        }

# schema to follow while adding a protocol
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
    default_answer: str = Field(
        default="I don't know. Please check with admin.")
    questions: list = Field(default={})
    archived_questions: list = Field(default={}) # in case you don't want to use the saved answer to a question, you can move the question here
    active: bool = Field(default=True)
    mod_responses: list = Field(default={})

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "protocol_id": "057gh609-b04a-5v54-b46c-32537c7c2c6e",
                "user_id": "066de609-b04a-4b30-b46c-32537c7f1f6e",
                "protocol_name": "Router Protocol",
                "protocol_description": "A cross-chain communication infra",
                "servers": {
                    "discord": {
                        "server": "1085331583558488104",
                        "question_limit_24hr": 5,
                        "refresh_days": 7,
                        "enable_mod_training": True
                    },
                    "telegram": {}
                },
                "doc_links": {"github": [{"url": "https://github.com/router-protocol/router-chain-docs",
                                          "doc_link": "https://devnet-docs.routerprotocol.com/",
                                          "directory": "docs"}, {"url": "xby", "doc_link": "abc", "directory": "docs"}],
                              "gitbook": [{"url": "abc"}, {"url": "xby"}]},
                "credits": 100.45,
                "usage": 0.34,
                "default_answer": "Please ask admin",
                "active": True,
                "questions": [{
                    "question": "",
                    "answer": "",
                    "embedding": "",
                    "usage": "",
                    "frequency": ""
                }],
                "archived_questions": [{
                    "question": "",
                    "answer": "",
                    "embedding": "",
                    "usage": "",
                    "frequency": ""
                }],
                "mod_responses": [{
                    "question": "",
                    "answer": "",
                    "server": "",
                    "added_time": "",
                    "is_trained": "",
                    "train_time": ""
                }]
            }
        }

# schema to follow while updating the details of a protocol
class ProtocolUpdate(BaseModel):
    protocol_name: Optional[str]
    protocol_description: Optional[str]
    servers: Optional[dict]
    doc_links: Optional[dict]
    credits: Optional[float]
    usage: Optional[float]
    default_answer: Optional[str]
    questions: Optional[dict]
    archived_questions: Optional[dict]
    active: Optional[bool]
    mod_responses: Optional[dict]

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "protocol_name": "Dfyn Exchange",
                "protocol_description": "Decentralized Exchange",
                "servers": {
                    "discord": {
                        "server": "1085331583558488104",
                        "question_limit_24hr": 5,
                        "refresh_days": 7,
                        "enable_mod_training": True
                    },
                    "telegram": {}
                },
                "doc_links": {"github": [{"url": "https://github.com/router-protocol/router-chain-docs",
                                          "doc_link": "https://devnet-docs.routerprotocol.com/",
                                          "directory": "docs"}, {"url": "xby", "doc_link": "abc", "directory": "docs"}],
                              "gitbook": [{"url": "abc"}, {"url": "xby"}]},
                "credits": 10.45,
                "usage": 8.97,
                "default_answer": "Please ask admin",
                "active": True,
                "questions": {
                    "question": "",
                    "answer": "",
                    "embedding": "",
                    "usage": "",
                    "frequency": ""
                },
                "archived_questions": {
                    "question": "",
                    "answer": "",
                    "embedding": "",
                    "usage": "",
                    "frequency": ""
                },
                "mod_responses": {
                    "question": "",
                    "answer": "",
                    "server": "",
                    "added_time": "",
                    "is_trained": "",
                    "train_time": ""
                }
            }
        }

# schema to follow while adding data (using which the bot will be trained) against a protocol
# this is how the data will be saved in the database
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

# schema to follow while posting the updated data to the database
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

# schema to follow while taking data from the user
# this is not how the data will be saved in the database
class DataFromUser(BaseModel):
    data_id: str = Field(default_factory=uuid.uuid4, alias="_id")
    data: dict = Field(...)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "data_id": "083jj669-s05c-4v63-b46c-98564c7c2c6e",
                "data": {
                    {"gitbook": [{"url": ""}, {"url": ""}]}, ## for multiple gitbook urls
                    {"github": [{"url": "https://github.com/router-protocol/router-chain-docs", "doc_link": "https://docs.routerprotocol.com/",
                                 "directory": "docs"}, {"url": "", "doc_link": "", "directory": ""}]},
                    {"pdf": [{"url": "https://routerprotocol.com/router-chain-whitepaper.pdf", "table_of_contents_pages": [2, 3]}]} # to skip table of content pages, you can also include other pages that you want to skip
                },
            }
        }

# schema to follow while taking updated data from the user
class DataFromUserUpdate(BaseModel):
    data: dict = Field(...)
    append: bool = Field(default=True)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "data": {},
                "append": True, # If True, new data will be appended to the existing data; if False, new data will replace the existing data
            }
        }

# schema to follow while saving the payment details for a protocol
class Payment(BaseModel):
    payment_id: str = Field(default_factory=uuid.uuid4, alias="_id")
    protocol_id: str = Field(...)
    payment_details: dict = Field(...)

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "payment_id": "083jj669-s05c-4v63-b46c-98564c7c2c6e",
                "protocol_id": "057gh609-b04a-5v54-b46c-32537c7c2c6e",
                "payment_details": {
                    "transaction_hash": "0xab6e20b7dea98e07adaa89c86a318d1409f1929e21c4f809599d16e217c882b6",
                    "chain_id": "56",
                    "chain": "BSC",
                    "token_address": "0x0cbA60Ca5eF4D42f92A5070A8fEDD13BE93E2861",
                    "token_symbol": "USDC",
                    "amount": 10
                },
            }
        }

# schema to follow while updating the payment details for a protocol
class PaymentUpdate(BaseModel):
    protocol_id: Optional[str]
    payment_details: Optional[dict]

    class Config:
        schema_extra = {
            "example": {
                "payment_id": "083jj669-s05c-4v63-b46c-98564c7c2c6e",
                "protocol_id": "057gh609-b04a-5v54-b46c-32537c7c2c6e",
                "payment_details": {
                    "transaction_hash": "0xab6e20b7dea98e07adaa89c86a318d1409f1929e21c4f809599d16e217c882b6",
                    "chain_id": "56",
                    "chain": "BSC",
                    "token_address": "0x0cbA60Ca5eF4D42f92A5070A8fEDD13BE93E2861",
                    "token_symbol": "USDC",
                    "amount": 10
                },
            }
        }
