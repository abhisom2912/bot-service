from fastapi import FastAPI
from dotenv import dotenv_values
from pymongo import MongoClient
from user_routes import user_router
from protocol_routes import protocol_router
from data_routes import data_router, question_router
from payment_routes import payment_router

config = dotenv_values("../.env")

app = FastAPI()

@app.on_event("startup")
def startup_db_client():
    app.mongodb_client = MongoClient(config["ATLAS_URI"])
    app.database = app.mongodb_client[config["DB_NAME"]]
    print("Connected to the MongoDB database!")

@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()

app.include_router(user_router, tags=["users"], prefix="/user")
app.include_router(protocol_router, tags=["protocols"], prefix="/protocol")
app.include_router(data_router, tags=["data"], prefix="/data")
app.include_router(question_router, tags=["questions"], prefix="/question")
app.include_router(payment_router, tags=["payments"], prefix="/payment")

