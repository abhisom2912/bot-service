from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import dotenv_values
from pymongo import MongoClient
from user_routes import user_router
from protocol_routes import protocol_router
from data_routes import data_router, question_router
from payment_routes import payment_router
from misc_routes import misc_router


config = dotenv_values("../.env")

# using the FastAPI framework for faster and more robust REST APIs
app = FastAPI()

# origins from which the API requests will be allowed
origins = [
    "http://localhost:3000",
    "http://localhost",
    "https://scarlett-ui.vercel.app/"
]  # add your hosting URL in this list


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# including all the REST endpoints
app.include_router(user_router, tags=["users"], prefix="/user")
app.include_router(protocol_router, tags=["protocols"], prefix="/protocol")
app.include_router(data_router, tags=["data"], prefix="/data")
app.include_router(question_router, tags=["questions"], prefix="/question")
app.include_router(payment_router, tags=["payments"], prefix="/payment")
app.include_router(misc_router, tags=["misc"], prefix="/general")
