import uuid

from fastapi import APIRouter, Body, Request, Response, HTTPException, status
from fastapi.encoders import jsonable_encoder
from utilities.fetch_data import *
from utilities.utility_functions import *
from models import DataFromUser, DataFromUserUpdate, Data
import validators
from datetime import datetime
import os

data_router = APIRouter()
question_router = APIRouter()

EMBEDDING_COST = 0.0004
# COMPLETIONS_COST = 0.03
THRESHOLD_FOR_FUZZY = 0.97 # consider two strings to be similar if they have over 97% match

BASE_DIR= os.path.abspath(os.path.dirname(__file__))
PDF_DIR = BASE_DIR[0:BASE_DIR.find('bot-service')] + 'resources'

# calculating outputs and fetching embeddings using OpenAI for the data uploaded by the user
# we save the outputs and embeddings in our database so as not to calculate them everytime
def fetch_outputs_and_embeddings(protocol, data_type, datas):
    outputs = []
    document_embeddings = {}
    cost = 0
    if data_type == 'gitbook':
        for data in datas:
            if validators.url(data['url']):
                gitbook_data_type = 'whitepaper' if 'gitbook_data_type' not in data else data['gitbook_data_type']
                url = data['url'] if data['url'][-1] != '/' else data['url'][:-1]
                if len(outputs) == 0:
                    outputs, document_embeddings, cost_incurred = get_data_from_gitbook(gitbook_data_type, url,
                                                                                        protocol['protocol_name'])
                else:
                    gitbook_outputs, gitbook_document_embeddings, cost_incurred = get_data_from_gitbook(
                        gitbook_data_type, url, protocol['protocol_name'])
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
                url = data['url'] if data['url'][-1] != '/' else data['url'][:-1]
                directory = '' if 'directory' not in data else \
                    data['directory'] if data['directory'][-1] == '/' else data['directory'] + '/'
                if len(outputs) == 0:
                    # github_directory - the specific folder that we need to read within the github repo, if empty then we will read all
                    outputs, document_embeddings, cost_incurred = read_from_github(protocol['protocol_name'],
                                                                                   url, data['doc_link'],
                                                                                   directory)
                else:
                    github_outputs, github_document_embeddings, cost_incurred = read_from_github(
                        protocol['protocol_name'], url, data['doc_link'], directory)
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

    if data_type == 'pdf':
        file_number = 1
        for data in datas:
            if validators.url(data['url']):
                response = requests.get(data['url'])
                if response.status_code != 200:
                    raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE,
                                        detail=f"Unable to download/read the content from the link.")
                file_name = PDF_DIR + '/' + protocol['protocol_name'] + '_' + str(file_number) + '.pdf'
                with open(file_name, 'wb') as f:
                    f.write(response.content)

                if len(outputs) == 0:
                    print(data['table_of_contents_pages'])
                    outputs, document_embeddings, cost_incurred = get_pdf_whitepaper_data(file_name, data['table_of_contents_pages'], data['url'],
                                                                                        protocol['protocol_name'])
                else:
                    gitbook_outputs, gitbook_document_embeddings, cost_incurred = get_pdf_whitepaper_data(
                        file_name, data['table_of_contents_pages'], data['url'], protocol['protocol_name'])
                    # append the new output to the outputs in the database
                    outputs.extend(gitbook_outputs)
                    # append the new embedding to the embedding in the database
                    document_embeddings.update(gitbook_document_embeddings)
                cost += cost_incurred
                file_number = file_number + 1
            else:
                print("Empty or invalid pdf link")
    return outputs, document_embeddings, cost


# API to save iterable data for a protocol
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


# API to update iterable data for a protocol
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
                                detail=f"A valid Gitbook/ GitHub/ PDF link has not been provided")
        else:
            data_from_db = request.app.database["data"].find_one(
                {"$and": [{"protocol_id": protocol_id}, {"data_type": key}]})
            if data_from_db is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Data for {key} doesn't exist, use post call")
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


# API to train the user's bot via moderator responses
# this will allow the bot to learn with information that is not included in the data provided by the user
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
    
    # only learning from moderator responses in user-specifed Discord servers
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

# API to fetch specific data
@data_router.get("/{protocol_id}/{data_type}", response_description="Get data by id", response_model=Data)
def find_data(protocol_id: str, data_type: str, request: Request):
    if (data := request.app.database["data"].find_one(
            {"$and": [{"_id": protocol_id}, {"data_type": data_type}]})) is not None:
        return data
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Data with protocol ID {protocol_id} not found")

# API to delete specific data
@data_router.delete("/{protocol_id}/{data_type}", response_description="Delete data")
def delete_data(protocol_id: str, data_type: str, request: Request, response: Response):
    delete_result = request.app.database["data"].delete_one({"$and": [{"_id": protocol_id}, {"data_type": data_type}]})

    if delete_result.deleted_count == 1:
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Data with protocol ID {protocol_id} not found")

# API to answer a question asked in any server (Discord/TG)
@question_router.get("/{server_type}/{server_id}/{questioner_server_id}",
                     response_description="Get answer to a question")
def answer_question_for_server(server_type: str, server_id: str, questioner_server_id: str, question: str,
                               request: Request):
    search_key = 'servers.' + server_type + '.server'
    # we first fetch the protocol against which the question was asked via its server_id
    protocol = request.app.database["protocols"].find_one({search_key: server_id})

    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Protocol for {server_type} with server id - {server_id} not found")
    
    # adding the questioner's new question to the database (since we rate limit the questioner, its important to maintain a mapping of the questioner's questions)
    update_questioner_data(protocol, question, questioner_server_id, request, server_type)
    
    # fetching the answer to the question
    question_answered, answer, links = get_answer(protocol, question, request)
    response = {"question_answered": question_answered, "answer": answer, "links": links}
    return response

# API to answer a question asked against a protocol
# the difference this API endpoint and the previous endpoint is that this endpoint takes only the protocol_id as an argument whereas the aforementioned endpoint fetches the protocol_id based on the server_id
# this API can be used if the questions are not being asked from a server but being asked via a Widget or directly via an API call
@question_router.get("/{protocol_id}", response_description="Get answer to a question")
def answer_question(protocol_id: str, question: str, request: Request):
    protocol = request.app.database["protocols"].find_one({"_id": protocol_id})
    if protocol is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Protocol with id {protocol_id} not found")
    question_answered, answer, links = get_answer(protocol, question, request)
    response = {"question_answered": question_answered, "answer": answer, "links": links}
    return response

# calculating the answer to a question based on a protocol's data
# we first check if the question already exists in the question/answer set in the database
# if true, we relay the saved answer to the questioner (cheaper)
# if false, we use OpenAI to fetch the answer from the user-uploaded data (a little expensive)
def get_answer(protocol, question, request):
    if not protocol['active']:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Protocol with protocol ID {protocol['_id']} is inactive")
    data_from_db = request.app.database["data"].find({"protocol_id": protocol['_id']})
    if (protocol['usage'] + 0.4) > protocol['credits']:
        raise HTTPException(status_code=status.HTTP_424_FAILED_DEPENDENCY,
                            detail=f"Insufficient credits to answer this question")
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

# archiving question/answer sets that are no longer needed
# while answering previously asked questions, Scarlett won't iterate through archived questions
def archive_existing_questions(protocol_id, request):
    protocol = request.app.database["protocols"].find_one({"_id": protocol_id})
    protocol['archived_questions'] = protocol['archived_questions'] + protocol['questions']
    protocol['questions'] = []
    update_result = request.app.database["protocols"].update_one(
        {"_id": protocol_id}, {"$set": protocol}
    )
    return request.app.database["protocols"].find_one({"_id": protocol_id})

# adding the questioner's new question in the mapping present in the database
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


# API to get an answer to a question using aggregated data from all uploaded protocol
@question_router.get("/masterApi/getAnswerFromAnyProtocol", response_description="Get answer to a question")
def answer_question(question: str, request: Request):
    question_answered, answer, links = get_answer_all_protocols(question, request)
    response = {"question_answered": question_answered, "answer": answer, "links": links}
    return response

# calculating the answer to a question based on data uploaded across all protocols
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