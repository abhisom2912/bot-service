from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder
from utilities.fetch_data import *
from utilities.utility_functions import *
from models import DataFromUser, DataFromUserUpdate, Data, DataUpdate
import validators

data_router = APIRouter()
question_router = APIRouter()

EMBEDDING_COST = 0.0004
COMPLETIONS_COST = 0.03


def fetch_outputs_and_embeddings(protocol, data):
    outputs = []
    document_embeddings = {}
    cost = 0
    if 'gitbook' in data.data.keys():
        if validators.url(data.data['gitbook']):
            print(data.data['gitbook'])
            gitbook_data_type = "whitepaper"
            outputs, document_embeddings, cost_incurred = get_data_from_gitbook(gitbook_data_type, data.data['gitbook'])
            cost += cost_incurred
        else:
            print("Empty or invalid GitBook link")
    if 'github' in data.data.keys():
        if validators.url(data.data['github']) and 'github' in data.data['github']:
            if len(outputs) == 0:
                print(protocol['protocol_name'])
                print(data.data['github'])
                outputs, document_embeddings, cost_incurred = read_from_github(protocol['protocol_name'], data.data['github']) 
                cost += cost_incurred
            else:
                github_outputs, github_document_embeddings, cost_incurred_from_github = read_from_github(protocol['protocol_name'], data.data['github']) 
                # append the new output to the outputs in the database
                outputs.extend(github_outputs)
                # append the new embedding to the embedding in the database
                document_embeddings.update(github_document_embeddings)
                cost += cost_incurred_from_github
        else:
            print("Empty or invalid GitHub link")
    return outputs, document_embeddings, cost

@data_router.post("/{user_id}/{protocol_id}", response_description="Create data for a protocol", status_code=status.HTTP_201_CREATED, response_model=Data)
def create_data(user_id: str, protocol_id: str, request: Request, data: DataFromUser = Body(...)):
    protocol = request.app.database["protocols"].find_one({ "$and": [ { "_id": protocol_id }, { "user_id": user_id } ] })
    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No protocol with user ID {user_id} and protocol ID {protocol_id} found")    
    if (protocol['usage'] + 0.2) > protocol['credits']:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=f"Insufficient credits to upload this data")
    if request.app.database["data"].find_one( {"protocol_id": protocol_id} ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Data for this protocol already exists. If you want to update the data, please use the update endpoint.")    
    print(data.data)
    outputs, document_embeddings, cost = fetch_outputs_and_embeddings(protocol, data)
    protocol['usage'] += cost
    update_result = request.app.database["protocols"].update_one(
            {"_id": protocol_id}, {"$set": protocol}
        )
    if len(outputs) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"A valid Gitbook or GitHub link has not been provided")    
    else:
        data_to_post = {"_id": data.data_id, "protocol_id": protocol_id, "data": outputs, "embeddings": untuplify_dict_keys(document_embeddings), "embeddings_cost": cost, "questions": []}
        new_data = request.app.database["data"].insert_one(jsonable_encoder(data_to_post))
        created_data = request.app.database["data"].find_one(
            {"_id": new_data.inserted_id}
        )
        user = request.app.database["users"].find_one( {"_id": user_id} )
        send_mail(user['mail'])
        return created_data

@data_router.put("/{user_id}/{protocol_id}", response_description="Update data", response_model=Data)
def update_data(user_id: str, protocol_id:str, request: Request, data: DataFromUserUpdate = Body(...)):
    protocol = request.app.database["protocols"].find_one({ "$and": [ { "_id": protocol_id }, { "user_id": user_id } ] })
    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No protocol with user ID {user_id} and protocol ID {protocol_id} found")    
    if (protocol['usage'] + 0.2) > protocol['credits']:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=f"Insufficient credits to upload this data")
    outputs, document_embeddings, cost = fetch_outputs_and_embeddings(protocol, data)
    protocol['usage'] += cost
    update_result = request.app.database["protocols"].update_one(
            {"_id": protocol_id}, {"$set": protocol}
        )
    if len(outputs) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"A valid Gitbook or GitHub link has not been provided")    
    else:
        data_from_db = request.app.database["data"].find_one({"protocol_id": protocol_id})
        cost_from_db = data_from_db['embeddings_cost']
        if data.append:
            outputs_from_db = data_from_db['data']
            document_embeddings_from_db = tuplify_dict_keys(data_from_db['embeddings'])
            outputs.extend(outputs_from_db)
            document_embeddings.update(document_embeddings_from_db)

        data_to_post = {"data": outputs, "embeddings": untuplify_dict_keys(document_embeddings), "embeddings_cost": (cost_from_db + cost)}
        update_result = request.app.database["data"].update_one(
            {"protocol_id": protocol_id}, {"$set": jsonable_encoder(data_to_post)}
        )
        updated_data = request.app.database["data"].find_one(
        {"protocol_id": protocol_id}
    )
        return updated_data


@data_router.get("/{protocol_id}", response_description="Get data by id", response_model=Data)
def find_data(protocol_id: str, request: Request):
    if (data := request.app.database["data"].find_one({"protocol_id": protocol_id})) is not None:
        return data
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with protocol ID {protocol_id} not found")


@data_router.delete("/{protocol_id}", response_description="Delete data")
def delete_data(protocol_id: str, request: Request, response: Response):
    delete_result = request.app.database["data"].delete_one({"protocol_id": protocol_id})

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with protocol ID {protocol_id} not found")


@question_router.get("/{protocol_id}", response_description="Get answer to a question")
def answer_question(protocol_id: str, question: str, request: Request):
    data_from_db = request.app.database["data"].find_one({"protocol_id": protocol_id})
    protocol = request.app.database["protocols"].find_one({"_id": protocol_id})
    if (protocol['usage'] + 0.4) > protocol['credits']:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY, detail=f"Insufficient credits to upload this data")
    if data_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data for protocol with ID {protocol_id} not found")
   
    outputs_from_db = data_from_db['data']
    questions_from_db = data_from_db["questions"]



    document_embeddings_from_db = tuplify_dict_keys(data_from_db['embeddings'])
    df_from_db = final_data_for_openai(outputs_from_db)
    question_embedding, tokens = get_embedding(question)
    question_cost = tokens * EMBEDDING_COST / 1000
    # question_similarities = sorted([
    #     (vector_similarity(question_embedding, prev_questions_embeddings[prev_question]), prev_question) for 'question' in questions_from_db.keys()
    # ], reverse=True)

    answer, answer_cost = answer_query_with_context(question, question_embedding, df_from_db, document_embeddings_from_db)
    total_cost_for_answer = question_cost + answer_cost
    protocol['usage'] += total_cost_for_answer

    update_result = request.app.database["protocols"].update_one(
            {"_id": protocol_id}, {"$set": protocol}
        )

    question_to_add = {"question": question, "answer": answer, "embedding": question_embedding, "usage": total_cost_for_answer}
    questions_from_db.append(question_to_add)
    data_to_post = {"questions": questions_from_db}
    update_result = request.app.database["data"].update_one(
            {"protocol_id": protocol_id}, {"$set": jsonable_encoder(data_to_post)}
        )

    return answer

# @question_router.post("/{protocol_id}", response_description="Add a new question", status_code=status.HTTP_201_CREATED, response_model=Data)
# def add_question(request: Request, question: DataUpdate = Body(...)):
#     question = jsonable_encoder(question)
#     new_question = request.app.database["data"].insert_one(question)
#     created_question = request.app.database["questions"].find_one(
#         {"_id": new_question.inserted_id}
#     )

#     return created_question

# @question_router.get("/", response_description="List all questions", response_model=list[Question])
# def list_questions(request: Request):
#     questions = list(request.app.database["questions"].find(limit=100))
#     return questions


# def add_data(request: Request, data: Data = Body(...)):
#     data = jsonable_encoder(data)
#     # if (protocol := request.app.database["protocols"].find_one({"_id": data['protocol_id']})) is None:
#     #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No protocol with ID {data['protocol_id']} found")       
#     new_data = request.app.database["data"].insert_one(data)
#     created_data = request.app.database["data"].find_one(
#         {"_id": new_data.inserted_id}
#     )
#     return created_data

# @data_router.post("/curated_data", response_description="Add data for a protocol", status_code=status.HTTP_201_CREATED, response_model=Data)
# def add_data(request: Request, data: Data = Body(...)):
#     # make it so that users cannot access this, only for internal calls
#     data = jsonable_encoder(data)
#     if (protocol := request.app.database["protocols"].find_one({"_id": data['protocol_id']})) is None:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No protocol with ID {data['protocol_id']} found")       
#     new_data = request.app.database["data"].insert_one(data)
#     created_data = request.app.database["data"].find_one(
#         {"_id": new_data.inserted_id}
#     )

#     return created_data


# @data_router.put("/{id}", response_description="Update data", response_model=Data)
# def update_data(id: str, request: Request, data: DataUpdate = Body(...)):
#     data = {k: v for k, v in data.dict().items() if v is not None}
#     if len(data) >= 1:
#         update_result = request.app.database["data"].update_one(
#             {"_id": id}, {"$set": data}
#         )

#         if update_result.modified_count == 0:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with ID {id} not found")

#     if (
#         existing_data := request.app.database["data"].find_one({"_id": id})
#     ) is not None:
#         return existing_data

#     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with ID {id} not found")
