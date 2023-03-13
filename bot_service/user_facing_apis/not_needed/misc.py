import multiprocessing
import gspread

TOKEN = "5922680401:AAEKq1oh0hP1RBky4ymL7lbXzhqnfTCRc3Q"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)

SHEET_ID = '1ve2d13qfafxTm-Gz6Hl1535Xag-ZWbHUU9-FhFe3GKw'
SHEET_NAME = 'Data Upload'


def echo_all(updates, df, document_embeddings):
    for update in updates["result"]:
        try:
            text = update["message"]["text"]
            chat = update["message"]["chat"]["id"]
            send_message(text, chat, df, document_embeddings)
        except Exception as e:
            print(e)

def send_message(text, chat_id, df, document_embeddings):
    print(text)
    response = answer_query_with_context(text, df, document_embeddings)
    url = URL + "sendMessage?text={}&chat_id={}".format(response, chat_id)
    get_url(url)


def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js

def get_updates(offset=None):
    url = URL + "getUpdates?timeout=100"
    if offset:
        url += "&offset={}".format(offset)
    js = get_json_from_url(url)
    return js

def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)


class TelegramBot(multiprocessing.Process):
    def __init__(self, df, document_embeddings):
        super(TelegramBot, self).__init__()
        self.df = df
        self.document_embeddings = document_embeddings

    def run(self):
        print("I'm the process with id: {}".format(self.df))
        last_update_id = None
        while True:
            updates = get_updates(last_update_id)
            if len(updates["result"]) > 0:
                last_update_id = get_last_update_id(updates) + 1
                echo_all(updates, self.df, self.document_embeddings)
            time.sleep(0.5)

class DiscordBot(multiprocessing.Process):
    def __init__(self, df, document_embeddings):
        super(DiscordBot, self).__init__()
        self.df = df
        self.document_embeddings = document_embeddings

    def run(self):
        print("I'm the process with id: {}".format(self.df))
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            print('We have logged in as {0.user}'.format(client))

        @client.event
        async def on_message(message):
            print(message.content)
            if message.author == client.user:
                return

            if message.content.lower().find('@1064872402003169312'.lower()) != -1:
                answer = answer_query_with_context(message.content, self.df, self.document_embeddings)
                await message.channel.send(answer)
                question  = message.content.replace('<@1064872402003169312> ', '')
                send_question_to_db(bot_id, question, answer)

        client.run(config['DISCORD_TOKEN'])


def send_question_to_db(bot_id, question, answer):
    data_to_post = {"bot_id": bot_id, "question": question, "answer": answer}
    response = requests.post(config['BASE_API_URL'] + "question/", json=data_to_post)
    return response

def send_to_db(_id, description, outputs, document_embeddings):
    data_to_post = {"_id": _id, "description": description, "data": outputs, "embeddings": untuplify_dict_keys(document_embeddings)}
    response = requests.post(config['BASE_API_URL'] + "document/", json=data_to_post)
    return response

def retrieve_from_db(_id):
    response = requests.get(config['BASE_API_URL'] + "document/" + _id)
    json_response = response.json()
    outputs = json_response['data']
    document_embeddings = tuplify_dict_keys(json_response['embeddings'])
    return outputs, document_embeddings

def update_in_db(outputs, embeddings, _id):
    # update the entry in the database
    data_to_update = {"data": outputs, "embeddings": untuplify_dict_keys(embeddings)}
    response = requests.put(config['BASE_API_URL'] + "document/" + _id, json=data_to_update)
    return response

def add_data(bot_id, title, heading, content):
    outputs, embeddings = retrieve_from_db(bot_id)
    # check to ensure that the output does not already include this entry
    for x in outputs:
        if(title == x[0] and heading == x[1] and content == x[2]):
            print("Data already present")
            return "Data already present"
    # take title, heading and content and fetch the new outputs
    new_outputs = calculate_new_output(title, heading, content)
    new_df = final_data_for_openai(new_outputs)
    # create an embedding against the newly added data
    new_document_embeddings = compute_doc_embeddings(new_df)
    # append the new output to the outputs in the database
    outputs.extend(new_outputs)
    # append the new embedding to the embedding in the database
    embeddings.update(new_document_embeddings)
    return update_in_db(outputs, embeddings, bot_id)

def update_data(bot_id, title, heading, updated_content):
    outputs, embeddings = retrieve_from_db(bot_id)
    index_to_delete = -1
    for i, x in enumerate(outputs):
        if(title == x[0] and heading == x[1]):
            if updated_content == x[2]:
                return "Updated data already present"
            else:
                index_to_delete = i
    if(index_to_delete > 0):
        new_outputs = calculate_new_output(title, heading, updated_content)
        new_df = final_data_for_openai(new_outputs)
        # create an embedding against the newly added data
        new_document_embeddings = compute_doc_embeddings(new_df)
        # append the new output to the outputs in the database
        outputs.extend(new_outputs)
        # append the new embedding to the embedding in the database
        embeddings.update(new_document_embeddings)
        # deleting the existing entry
        updated_outputs, updated_embeddings = delete_entries_by_index(outputs, embeddings, index_to_delete)
    return update_in_db(updated_outputs, updated_embeddings, bot_id)

def delete_data(bot_id, title, heading):
    outputs, embeddings = retrieve_from_db(bot_id)
    index_to_delete = -1
    for i, x in enumerate(outputs):
        if(title == x[0] and heading == x[1]):
            index_to_delete = i
    if index_to_delete<0:
        return "Title and heading not found"
    updated_outputs, updated_embeddings = delete_entries_by_index(outputs, embeddings, index_to_delete)
    return update_in_db(updated_outputs, updated_embeddings, bot_id)
    
def delete_entries_by_index(outputs, embeddings, index):
    outputs.pop(index)
    # del embeddings[next(islice(embeddings, index, None))]
    return outputs, embeddings


def calculate_new_output(title, heading, content):
    nheadings, ncontents, ntitles = [], [], []
    outputs = []
    max_len = 1500
    nheadings.append(heading)
    ncontents.append(content)
    ntitles.append(title)
    ncontent_ntokens = [
        count_tokens(c)
        + 3
        + count_tokens(" ".join(h.split(" ")[1:-1]))
        - (1 if len(c) == 0 else 0)
        for h, c in zip(nheadings, ncontents)
    ]

    for title, h, c, t in zip(ntitles, nheadings, ncontents, ncontent_ntokens):
        if (t<max_len and t>min_token_limit):
            outputs += [(title,h,c,t)]
        elif(t>=max_len):
            outputs += [(title, h, reduce_long(c, max_len), count_tokens(reduce_long(c,max_len)))]

    return outputs



def load_embeddings(fname: str) -> dict[tuple[str, str], list[float]]:
    """
    Read the document embeddings and their keys from a CSV.

    fname is the path to a CSV with exactly these named columns:
        "title", "heading", "0", "1", ... up to the length of the embedding vectors.
    """

    df = pd.read_csv(fname, header=0)
    max_dim = max([int(c) for c in df.columns if c != "title" and c != "heading"])
    return {
        (r.title, r.heading): [r[str(i)] for i in range(max_dim + 1)] for _, r in df.iterrows()
    }


def answer_query_with_context(
		query: str,
		df: pd.DataFrame,
		document_embeddings: dict[tuple[str, str], np.array],
		show_prompt: bool = False
) -> str:
    prompt = construct_prompt(
		query,
		document_embeddings,
		df
	)
    if show_prompt:
        print(prompt)

    response = openai.Completion.create(
		prompt=prompt,
		**COMPLETIONS_API_PARAMS
	)

    return response["choices"][0]["text"].strip(" \n")