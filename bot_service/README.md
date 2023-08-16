## To run the mongo server:
1) Install the prerequisites:
- fastapi
- pymongo
- uvicorn
- pydantic
- uuid
2) Inside the mongo_service directory, run the following command:
- `python3 -m uvicorn mongo_server:app --reload`
3) After running the mongo server using the command given above, you can check out the Swagger generated API docs here: http://127.0.0.1:8000/docs#/ or the FastAPI generated API docs here: http://127.0.0.1:8000/redoc 

## Run the python script after running the mongo server (in a separate terminal). To do so, run the following command in the base directory:
- `python3 all_bot_openai_py310.py`
