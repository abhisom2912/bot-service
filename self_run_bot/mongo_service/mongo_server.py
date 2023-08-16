from fastapi import FastAPI
from dotenv import dotenv_values
from pymongo import MongoClient
from routes import document_router

config = dotenv_values("../.env")

# using the FastAPI framework for faster and more robust REST APIs
app = FastAPI()

# upon starting the application, we are initializing the Mongo connection and connecting to our database
@app.on_event("startup")
def startup_db_client():
    app.mongodb_client = MongoClient(config["ATLAS_URI"])
    app.database = app.mongodb_client[config["DB_NAME"]]
    print("Connected to the MongoDB database!")

# closing the Mongo connection on shutdown
@app.on_event("shutdown")
def shutdown_db_client():
    app.mongodb_client.close()

# including all the REST endpoints for documents
app.include_router(document_router, tags=["documents"], prefix="/document")
