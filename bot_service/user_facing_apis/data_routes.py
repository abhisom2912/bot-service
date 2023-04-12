import uuid

from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder
from utilities.fetch_data import *
from utilities.utility_functions import *
from models import DataFromUser, DataFromUserUpdate, Data
import validators
from datetime import datetime

data_router = APIRouter()
question_router = APIRouter()

EMBEDDING_COST = 0.0004
COMPLETIONS_COST = 0.03
THRESHOLD_FOR_FUZZY = 0.95


# {"gitbook":[{"url":"abc"}, {"url":"xby"}]}
# {"github":[{"url":"https://github.com/router-protocol/router-chain-docs", "doc_link":"https://devnet-docs.routerprotocol.com/", "directory":"docs"}, {"url":"xby", "doc_link":"abc", "directory":"docs"}]}
def fetch_outputs_and_embeddings(protocol, data_type, datas):
    outputs = []
    document_embeddings = {}
    cost = 0
    if data_type == 'gitbook':
        for data in datas:
            if validators.url(data['url']):
                gitbook_data_type = 'whitepaper' if 'gitbook_data_type' not in data else data['gitbook_data_type']
                if len(outputs) == 0:
                    outputs, document_embeddings, cost_incurred = get_data_from_gitbook(gitbook_data_type, data['url'],
                                                                                        protocol['protocol_name'])
                else:
                    gitbook_outputs, gitbook_document_embeddings, cost_incurred = get_data_from_gitbook(
                        gitbook_data_type, data['url'], protocol['protocol_name'])
                    # append the new output to the outputs in the database
                    outputs.extend(gitbook_outputs)
                    # append the new embedding to the embedding in the database
                    document_embeddings.update(gitbook_document_embeddings)
                cost += cost_incurred
            else:
                print("Empty or invalid GitBook link")

    if data_type == 'github':
        for data in datas:
            if validators.url(data['url']) and 'github' in data['url']:
                directory = '' if 'directory' not in data else data['directory']
                if len(outputs) == 0:
                    # github_directory - the specific folder that we need to read within the github repo, if empty then we will read all
                    outputs, document_embeddings, cost_incurred = read_from_github(protocol['protocol_name'],
                                                                                   data['url'], data['doc_link'],
                                                                                   directory)
                else:
                    github_outputs, github_document_embeddings, cost_incurred = read_from_github(
                        protocol['protocol_name'], data['url'], data['doc_link'], directory)
                    # append the new output to the outputs in the database
                    outputs.extend(github_outputs)
                    # append the new embedding to the embedding in the database
                    document_embeddings.update(github_document_embeddings)
                cost += cost_incurred
            else:
                print("Empty or invalid GitHub link")

    if data_type == 'medium':
        for data in datas:
            if data['username'][0] == '@':
                duration = 10000 if 'valid_articles_duration_days' not in data else data['valid_articles_duration_days']
                if len(outputs) == 0:
                    outputs, document_embeddings, cost_incurred = get_data_from_medium(data['username'],
                                                                                       duration,
                                                                                       protocol['protocol_name'])
                else:
                    medium_outputs, medium_document_embeddings, cost_incurred = get_data_from_medium(data['username'],
                                                                                                     duration, protocol[
                                                                                                         'protocol_name'])
                    # append the new output to the outputs in the database
                    outputs.extend(medium_outputs)
                    # append the new embedding to the embedding in the database
                    document_embeddings.update(medium_document_embeddings)
                cost += cost_incurred
            else:
                print("Empty or invalid Medium details")
    return outputs, document_embeddings, cost


@data_router.post("/{user_id}/{protocol_id}", response_description="Create data for a protocol",
                  status_code=status.HTTP_201_CREATED, response_model=Data)
def create_data(user_id: str, protocol_id: str, request: Request, data: DataFromUser = Body(...)):
    protocol = request.app.database["protocols"].find_one({"$and": [{"_id": protocol_id}, {"user_id": user_id}]})

    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No protocol with user ID {user_id} and protocol ID {protocol_id} found")
    if not protocol['active']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Protocol with protocol ID {protocol_id} is inactive")
    if (protocol['usage'] + 0.2) > protocol['credits']:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY,
                            detail=f"Insufficient credits to upload this data")
    for data_type in data.data.keys():
        if request.app.database["data"].find_one({"$and": [{"protocol_id": protocol_id}, {"data_type": data_type}]}):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail=f"Data for this protocol and data type already exists. If you want to update the data, please use the update endpoint.")

    for key in data.data.keys():
        outputs, document_embeddings, cost = fetch_outputs_and_embeddings(protocol, key, data.data[key])
        protocol['usage'] += cost
        if len(outputs) == 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"A valid Gitbook or GitHub link has not been provided")
        else:
            data_to_post = {"_id": data.data_id, "protocol_id": protocol_id, "data": outputs, "data_type": key,
                            "embeddings": untuplify_dict_keys(document_embeddings), "embeddings_cost": cost}
            new_data = request.app.database["data"].insert_one(jsonable_encoder(data_to_post))

    if new_data is None:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail=f"No data inserted in the DB")

    created_data = request.app.database["data"].find_one(
        {"_id": new_data.inserted_id}
    )

    protocol['doc_links'].update(data.data)
    user = request.app.database["users"].find_one({"_id": user_id})
    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol_id}, {"$set": protocol}
    )
    protocol = archive_existing_questions(protocol_id, request)
    send_mail(user['email'])
    return created_data



@data_router.put("/{user_id}/{protocol_id}", response_description="Update data", response_model=Data)
def update_data(user_id: str, protocol_id: str, request: Request, data: DataFromUserUpdate = Body(...)):
    protocol = request.app.database["protocols"].find_one({"$and": [{"_id": protocol_id}, {"user_id": user_id}]})

    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No protocol with user ID {user_id} and protocol ID {protocol_id} found")
    if not protocol['active']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Protocol with protocol ID {protocol_id} is inactive")
    if (protocol['usage'] + 0.2) > protocol['credits']:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY,
                            detail=f"Insufficient credits to upload this data")

    for key in data.data.keys():
        outputs, document_embeddings, cost = fetch_outputs_and_embeddings(protocol, key, data.data[key])
        protocol['usage'] += cost
        update_result = request.app.database["protocols"].update_one(
            {"_id": protocol_id}, {"$set": protocol}
        )
        if len(outputs) == 0:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                                detail=f"A valid Gitbook or GitHub link has not been provided")
        else:
            data_from_db = request.app.database["data"].find_one(
                {"$and": [{"protocol_id": protocol_id}, {"data_type": key}]})
            cost_from_db = data_from_db['embeddings_cost']
            if data.append:
                outputs_from_db = data_from_db['data']
                document_embeddings_from_db = tuplify_dict_keys(data_from_db['embeddings'])
                outputs.extend(outputs_from_db)
                document_embeddings.update(document_embeddings_from_db)
                protocol['doc_links'][key] = protocol['doc_links'][key] + data.data[key]
            else:
                protocol['doc_links'][key] = data.data[key]

            data_to_post = {"data": outputs, "embeddings": untuplify_dict_keys(document_embeddings),
                            "embeddings_cost": (cost_from_db + cost)}
            update_result = request.app.database["data"].update_one(
                {"$and": [{"protocol_id": protocol_id}, {"data_type": key}]},
                {"$set": jsonable_encoder(data_to_post)}
            )
            updated_data = request.app.database["data"].find_one(
                {"$and": [{"protocol_id": protocol_id}, {"data_type": key}]}
            )

    if updated_data is None:
        raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail=f"No data updated in the DB")

    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol_id}, {"$set": protocol}
    )
    protocol = archive_existing_questions(protocol_id, request)
    return updated_data


@data_router.put("/trainUsingModResponses", response_description="Train using mod responses")
def train_using_mod_responses(request: Request, protocol_id: str=Body(...), reset: bool=Body(...)):
    protocol = request.app.database["protocols"].find_one({"_id": protocol_id})

    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No protocol with protocol ID {protocol_id} found")
    if not protocol['active']:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Protocol with protocol ID {protocol_id} is inactive")
    if (protocol['usage'] + 0.2) > protocol['credits']:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY,
                            detail=f"Insufficient credits to upload this data")

    valid_servers_for_training = {key : val for key, val in protocol['servers'].items() if 'enable_mod_training' in val.keys() and val['enable_mod_training']}
    if not reset:
        filtered_arr = [response for response in protocol['mod_responses'] if not response['is_trained']
                        and response['server'] in valid_servers_for_training.keys() and
                        (datetime.now() - response['added_time'] <=
                         timedelta(seconds=valid_servers_for_training[response['server']]['mod_training_valid_days'] * 24 * 60 * 60)
                         if 'mod_training_valid_days' in valid_servers_for_training[response['server']].keys() is not None else True)]
    else:
        filtered_arr = [response for response in protocol['mod_responses'] if response['server'] in
                        valid_servers_for_training.keys() and (datetime.now() - response['added_time'] <=
                         timedelta(seconds=valid_servers_for_training[response['server']]['mod_training_valid_days'] * 24 * 60 * 60)
                         if 'mod_training_valid_days' in valid_servers_for_training[response['server']].keys() is not None else True)]

    if len(filtered_arr) == 0:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail=f"Nothing to train from")

    outputs, document_embeddings, cost = get_data_for_mod_responses(filtered_arr, protocol['protocol_name'])

    data_from_db = request.app.database["data"].find_one(
        {"$and": [{"protocol_id": protocol_id}, {"data_type": 'mod_responses'}]})
    protocol['usage'] += cost

    if data_from_db is None:
        data_to_post = {"_id": uuid.uuid4(), "protocol_id": protocol_id, "data": outputs, "data_type": 'mod_responses',
                        "embeddings": untuplify_dict_keys(document_embeddings), "embeddings_cost": cost}
        new_data = request.app.database["data"].insert_one(jsonable_encoder(data_to_post))
    else:
        cost_from_db = data_from_db['embeddings_cost']
        if not reset:
            outputs_from_db = data_from_db['data']
            document_embeddings_from_db = tuplify_dict_keys(data_from_db['embeddings'])
            outputs.extend(outputs_from_db)
            document_embeddings.update(document_embeddings_from_db)
        data_to_post = {"data": outputs, "embeddings": untuplify_dict_keys(document_embeddings),
                        "embeddings_cost": (cost_from_db + cost)}
        update_result = request.app.database["data"].update_one(
            {"$and": [{"protocol_id": protocol_id}, {"data_type": 'mod_responses'}]},
            {"$set": jsonable_encoder(data_to_post)}
        )

    updated_ids = [value['id'] for value in filtered_arr]
    for response in protocol['mod_responses']:
        if response['id'] in updated_ids:
            response['is_trained'] = True
            response['train_time'] = datetime.now()

    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol_id}, {"$set": protocol}
    )
    protocol = archive_existing_questions(protocol_id, request)
    return {'status' : 'bot successfully trained with mod reponses data'}


@data_router.get("/{protocol_id}/{data_type}", response_description="Get data by id", response_model=Data)
def find_data(protocol_id: str, data_type: str, request: Request):
    if (data := request.app.database["data"].find_one(
            {"$and": [{"_id": protocol_id}, {"data_type": data_type}]})) is not None:
        return data
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Data with protocol ID {protocol_id} not found")


@data_router.delete("/{protocol_id}/{data_type}", response_description="Delete data")
def delete_data(protocol_id: str, data_type: str, request: Request, response: Response):
    delete_result = request.app.database["data"].delete_one({"$and": [{"_id": protocol_id}, {"data_type": data_type}]})

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with protocol ID {protocol_id} not found")


@question_router.get("/{server_type}/{server_id}/{questioner_server_id}",
                     response_description="Get answer to a question")
def answer_question_for_server(server_type: str, server_id: str, questioner_server_id: str, question: str,
                               request: Request):
    search_key = 'servers.' + server_type + '.server'
    protocol = request.app.database["protocols"].find_one({search_key: server_id})

    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Protocol for {server_type} with server id - {server_id} not found")
    update_questioner_data(protocol, question, questioner_server_id, request, server_type)
    question_answered, answer, links = get_answer(protocol, question, request)
    response = {"question_answered": question_answered, "answer": answer, "links": links}
    return response


@question_router.get("/{protocol_id}", response_description="Get answer to a question")
def answer_question(protocol_id: str, question: str, request: Request):
    protocol = request.app.database["protocols"].find_one({"_id": protocol_id})
    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Protocol with id {protocol_id} not found")
    question_answered, answer, links = get_answer(protocol, question, request)
    response = {"question_answered": question_answered, "answer": answer, "links": links}
    return response


def get_answer(protocol, question, request):
    if not protocol['active']:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Protocol with protocol ID {protocol['_id']} is inactive")
    data_from_db = request.app.database["data"].find({"protocol_id": protocol['_id']})
    if (protocol['usage'] + 0.4) > protocol['credits']:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY,
                            detail=f"Insufficient credits to upload this data")
    if data_from_db is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Data for protocol with ID {protocol['_id']} not found")
    outputs_from_db = []
    document_embeddings = {}
    for data in data_from_db:
        outputs_from_db.extend(data['data'])
        document_embeddings.update(data['embeddings'])
    questions_from_db = protocol['questions']
    document_embeddings_from_db = tuplify_dict_keys(document_embeddings)
    df_from_db = final_data_for_openai(outputs_from_db)
    question_embedding, tokens = get_embedding(question)
    question_cost = tokens * EMBEDDING_COST / 1000
    question_similarities = sorted([
        (vector_similarity(question_embedding, prev_question['embedding']), prev_question['answer'], prev_question) for
        prev_question in questions_from_db
    ], reverse=True)
    links = []
    if len(question_similarities) >= 1 and question_similarities[0][0] > THRESHOLD_FOR_FUZZY:
        answer = question_similarities[0][1]
        links = question_similarities[0][2]['links']
        total_cost_for_answer = question_cost
        request.app.database["protocols"].update_one(
            {"_id": protocol['_id'], 'questions.question': question_similarities[0][2]['question']},
            {"$set": {"questions.$.frequency": question_similarities[0][2]['frequency'] + 1}}
        )
    else:
        answer, answer_cost, links = answer_query_with_context(question, question_embedding, df_from_db,
                                                               document_embeddings_from_db, protocol['default_answer'])
        total_cost_for_answer = question_cost + answer_cost
        question_to_add = {"question": question, "answer": answer, "embedding": question_embedding, "links": links,
                           "usage": total_cost_for_answer, "frequency": 1}
        questions_from_db.append(question_to_add)
        # data_to_post = {"questions": questions_from_db}
        protocol['questions'] = questions_from_db
        update_result = request.app.database["protocols"].update_one(
            {"_id": protocol['_id']}, {"$set": protocol}
        )
    total_cost = protocol['usage'] + total_cost_for_answer
    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol['_id']}, {"$set": {"usage": total_cost}}
    )
    question_answered = False if answer == protocol['default_answer'] else True
    return question_answered, answer, links


def archive_existing_questions(protocol_id, request):
    protocol = request.app.database["protocols"].find_one({"_id": protocol_id})
    protocol['archived_questions'] = protocol['archived_questions'] + protocol['questions']
    protocol['questions'] = []
    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol_id}, {"$set": protocol}
    )
    return request.app.database["protocols"].find_one({"_id": protocol_id})


def update_questioner_data(protocol, question, questioner_server_id, request, server_type):
    rate_limit_exists = False
    try:
        rate_limit = protocol['servers'][server_type]['question_limit_24hr']
        rate_limit_exists = True
    except KeyError:
        pass

    questioner = request.app.database["questioners"].find_one(
        {"$and": [{"questioner_server_id": questioner_server_id}, {"server_type": server_type}]})
    protocol_id = protocol['_id']
    user_protocol_limit = {protocol_id: {"first_question_time": str(datetime.now()),
                                         "questions_asked": 1}}
    question_data = {protocol_id: [question]}

    if questioner is None:
        data_to_post = {"server_type": server_type, "questioner_server_id": questioner_server_id,
                        "user_protocol_limits": user_protocol_limit,
                        "questions": question_data, "_id": uuid.uuid4()}
        new_data = request.app.database["questioners"].insert_one(jsonable_encoder(data_to_post))
    else:
        protocol_search_query = "user_protocol_limits." + protocol_id
        questioner_protocol = request.app.database["questioners"].find_one(
            {"$and": [{protocol_search_query: {"$exists":True}},
                      {"questioner_server_id": questioner_server_id}, {"server_type": server_type}]})
        if questioner_protocol is None:
            questioner['questions'].update(question_data)
            questioner['user_protocol_limits'].update(user_protocol_limit)
            update_result = request.app.database["questioners"].update_one(
                {"_id": questioner['_id']}, {"$set": questioner}
            )
        else:
            time_difference = datetime.now() - datetime.strptime(
                questioner_protocol['user_protocol_limits'][protocol_id]['first_question_time'], '%Y-%m-%d %H:%M:%S.%f')
            if rate_limit_exists and time_difference.total_seconds() > 24 * 60 * 60:
                questioner_protocol['user_protocol_limits'][protocol_id]['questions_asked'] = 1
                questioner_protocol['user_protocol_limits'][protocol_id]['first_question_time'] = str(datetime.now())
                questioner_protocol['questions'][protocol_id].append(question)
            elif rate_limit_exists and time_difference.total_seconds() <= 24 * 60 * 60 and rate_limit == \
                    questioner_protocol['user_protocol_limits'][protocol_id]['questions_asked']:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail=f"Rate limit reached for user on {server_type} for {protocol['protocol_name']}")
            else:
                questioner_protocol['user_protocol_limits'][protocol_id]['questions_asked'] = \
                    questioner_protocol['user_protocol_limits'][protocol_id]['questions_asked'] + 1
                questioner_protocol['questions'][protocol_id].append(question)
            update_result = request.app.database["questioners"].update_one(
                {"_id": questioner_protocol["_id"]}, {"$set": questioner_protocol}
            )



@question_router.get("/masterApi/getAnswerFromAnyProtocol", response_description="Get answer to a question")
def answer_question(question: str, request: Request):
    question_answered, answer, links = get_answer_all_protocols(question, request)
    response = {"question_answered": question_answered, "answer": answer, "links": links}
    return response


def get_answer_all_protocols(question, request):
    default_answer = 'I am not sure of this. Please check with the admin!'
    data_from_db = request.app.database["data"].find()
    outputs_from_db, questions_from_db = [], []
    document_embeddings = {}
    for data in data_from_db:
        outputs_from_db.extend(data['data'])
        document_embeddings.update(data['embeddings'])

    protocols_from_db = request.app.database["protocols"].find()
    for protocol in protocols_from_db:
        if protocol['questions'] is not None and len(protocol['questions']) > 0:
            questions_from_db = questions_from_db + protocol['questions']

    document_embeddings_from_db = tuplify_dict_keys(document_embeddings)
    df_from_db = final_data_for_openai(outputs_from_db)

    question_embedding, tokens = get_embedding(question)
    question_similarities = sorted([
        (vector_similarity(question_embedding, prev_question['embedding']), prev_question['answer'], prev_question) for
        prev_question in questions_from_db
    ], reverse=True)
    if len(question_similarities) >= 1 and question_similarities[0][0] > THRESHOLD_FOR_FUZZY:
        answer = question_similarities[0][1]
        links = question_similarities[0][2]['links']
    else:
        answer, answer_cost, links = answer_query_with_context(question, question_embedding, df_from_db,
                                                               document_embeddings_from_db, default_answer)
    question_answered = False if answer == default_answer else True
    return question_answered, answer, links

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
