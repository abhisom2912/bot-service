
Three types of users:
1) Users who just want to run a simple Discord/TG bot that responds to users' questions using documentation present in Gitbook/Notion/PDF documents, among others.
2) Users who want to run a little more sophistacated Discord/TG bot that not only responds to users' questions, but stores those questions and answers so that the answers are not computed again via OpenAI
3) Users who want to offer this as a service

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
