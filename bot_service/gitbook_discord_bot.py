import discord
import json
import requests
import time
import urllib
from transformers import GPT2TokenizerFast

import numpy as np
from github import Github
from dotenv import dotenv_values
import os
import pyparsing as pp
import openai
import pandas as pd
import tiktoken
from nltk.tokenize import sent_tokenize
from typing import List
from typing import Dict
from typing import Tuple
import nltk
import gspread

from gitbook_scraper import *

nltk.download('punkt')
config = dotenv_values(".env")

bot_id = "3"
bot_description = "Klima Dao Bot"
SHEET_ID = '1ve2d13qfafxTm-Gz6Hl1535Xag-ZWbHUU9-FhFe3GKw'
SHEET_NAME = 'Data Upload'
min_token_limit = 10

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
COMPLETIONS_MODEL = "text-davinci-003"
EMBEDDING_MODEL = "text-embedding-ada-002"
MAX_SECTION_LEN = 500
SEPARATOR = "\n* "
ENCODING = "cl100k_base"

encoding = tiktoken.get_encoding(ENCODING)
separator_len = len(encoding.encode(SEPARATOR))

# f"Context separator contains {separator_len} tokens"


COMPLETIONS_API_PARAMS = {
    # We use temperature of 0.0 because it gives the most predictable, factual answer.
    "temperature": 0.0,
    "max_tokens": 300,
    "model": COMPLETIONS_MODEL,
}

def create_data_for_docs(title_stack) -> []:
    heads = {}
    max_level = 0
    nheadings, ncontents, ntitles = [], [], []
    outputs = []
    max_len = 1500
    s1 = '<Section'
    s2 = '</Section>'

    for level, header, content, dir in title_stack:
        final_header = header
        dir_elements = dir.split('/')
        element_len = 1
        dir_header = ''
        sub = 1
        title = 'Klima Dao' + " - " + dir_elements[0]
        if dir_elements[len(dir_elements) - sub].find('README') != -1:
            sub = sub + 1
        while element_len < len(dir_elements) - sub:
            dir_header = dir_header + dir_elements[element_len] + ': '
            element_len = element_len + 1

        if level > 0:
            heads[level] = header
            if level > max_level:
                max_level = level
            while max_level > level:
                try:
                    heads.pop(max_level)
                except Exception:
                    pass
                max_level = max_level - 1

        i = level - 1
        while i > 0:
            try:
                final_header = heads[i] + ': ' + final_header
            except Exception:
                pass
            i=i-1
        final_header = dir_header + final_header
        if final_header.find('start_of_file') == -1:
            remove_content = find_between(content, s1, s2)
            content = content.replace(remove_content,'').replace(s1, '').replace(s2, '')
            if content.strip() == '':
                continue
            nheadings.append(final_header.strip())
            ncontents.append(content)
            ntitles.append(title)

    ncontent_ntokens = [
        count_tokens(c)
        + 3
        + count_tokens(" ".join(h.split(" ")[1:-1]))
        - (1 if len(c) == 0 else 0)
        for h, c in zip(nheadings, ncontents)
    ]
    outputs += [(title, h, c, t) if t<max_len
                else (title, h, reduce_long(c, max_len), count_tokens(reduce_long(c,max_len)))
                for title, h, c, t in zip(ntitles, nheadings, ncontents, ncontent_ntokens)]
    return outputs

def add_data_array(file_path, content, title_stack):
    title = pp.AtLineStart(pp.Word("#")) + pp.rest_of_line
    title_stack.append([0, 'start_of_file'])
    if content.split('\n')[0] == '---':
        title_stack[-1].append('')
        title_stack[-1].append(file_path)
        title_stack.append([1, content.split('\n')[1].split(':')[1].lstrip()])
        content = content.split('---')[2]
    last_end = 0
    for t, start, end in title.scan_string(content):
        # save content since last title in the last item in title_stack
        title_stack[-1].append(content[last_end:start].lstrip("\n"))
        title_stack[-1].append(file_path)

        # add a new entry to title_stack
        marker, title_content = t
        level = len(marker)
        title_stack.append([level, title_content.lstrip()])

        # update last_end to the end of the current match
        last_end = end

    # add trailing text to the final parsed title
    title_stack[-1].append(content[last_end:])
    title_stack[-1].append(file_path)

def final_data_for_openai(outputs):
    res = []
    res += outputs
    df = pd.DataFrame(res, columns=["title", "heading", "content", "tokens"])
    df = df[df.tokens>40]
    df = df.drop_duplicates(['title','heading'])
    df = df.reset_index().drop('index',axis=1) # reset index
    df = df.set_index(["title", "heading"])
    return df


def count_tokens(text: str) -> int:
    """count the number of tokens in a string"""
    return len(tokenizer.encode(text))

def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.rindex( last, start )
        return s[start:end]
    except ValueError:
        return ""

def reduce_long(
        long_text: str, long_text_tokens: bool = False, max_len: int = 590
) -> str:
    """
    Reduce a long text to a maximum of `max_len` tokens by potentially cutting at a sentence end
    """
    if not long_text_tokens:
        long_text_tokens = count_tokens(long_text)
    if long_text_tokens > max_len:
        sentences = sent_tokenize(long_text.replace("\n", " "))
        ntokens = 0
        for i, sentence in enumerate(sentences):
            ntokens += 1 + count_tokens(sentence)
            if ntokens > max_len:
                return ". ".join(sentences[:i][:-1]) + "."

    return long_text

def get_embedding(text: str, model: str=EMBEDDING_MODEL) -> List[float]:
    time.sleep(7)
    result = openai.Embedding.create(
        model=model,
        input=text
    )
    return result["data"][0]["embedding"]

def compute_doc_embeddings(df: pd.DataFrame) -> Dict[Tuple[str, str], List[float]]:
    """
    Create an embedding for each row in the dataframe using the OpenAI Embeddings API.

    Return a dictionary that maps between each embedding vector and the index of the row that it corresponds to.
    """
    return {
        idx: get_embedding(r.content) for idx, r in df.iterrows()
    }

def load_embeddings(fname: str) -> Dict[Tuple[str, str], List[float]]:
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

def vector_similarity(x: List[float], y: List[float]) -> float:
    """
    Returns the similarity between two vectors.

    Because OpenAI Embeddings are normalized to length 1, the cosine similarity is the same as the dot product.
    """
    return np.dot(np.array(x), np.array(y))

def order_document_sections_by_query_similarity(query: str, contexts: Dict[Tuple[str, str], np.array]) -> List[Tuple[float, Tuple[str, str]]]:
    """
    Find the query embedding for the supplied query, and compare it against all of the pre-calculated document embeddings
    to find the most relevant sections.

    Return the list of document sections, sorted by relevance in descending order.
    """
    query_embedding = get_embedding(query)

    document_similarities = sorted([
        (vector_similarity(query_embedding, doc_embedding), doc_index) for doc_index, doc_embedding in contexts.items()
    ], reverse=True)

    return document_similarities

def construct_prompt(question: str, context_embeddings: dict, df: pd.DataFrame) -> str:
    """
    Fetch relevant
    """
    most_relevant_document_sections = order_document_sections_by_query_similarity(question, context_embeddings)

    chosen_sections = []
    chosen_sections_len = 0
    chosen_sections_indexes = []

    for _, section_index in most_relevant_document_sections:
        # Add contexts until we run out of space.
        document_section = df.loc[section_index]

        chosen_sections_len += document_section.tokens + separator_len
        if chosen_sections_len > MAX_SECTION_LEN:
            break

        chosen_sections.append(SEPARATOR + document_section.content.replace("\n", " "))
        chosen_sections_indexes.append(str(section_index))

    # Useful diagnostic information
    print("Selected {len(chosen_sections)} document sections:")
    print("\n".join(chosen_sections_indexes))

    header = """Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say "I don't know."\n\nContext:\n"""

    return header + "".join(chosen_sections) + "\n\n Q: " + question + "\n A:"

def answer_query_with_context(
        query: str,
        df: pd.DataFrame,
        document_embeddings: Dict[Tuple[str, str], np.array],
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

def untuplify_dict_keys(mapping):
    string_keys = {json.dumps(k): v for k, v in mapping.items()}
    return string_keys

def tuplify_dict_keys(string):
    mapping = string
    return {tuple(json.loads(k)): v for k, v in mapping.items()}

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

def add_data_from_sheet(bot_id, sheet_id, sheet_name):
    # TODO - Fix the below line
    gc = gspread.service_account('./credentials.json')
    spreadsheet = gc.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    rows = worksheet.get_all_records()
    print(rows)
    df = pd.DataFrame(rows)
    data_dict = {}
    upload_df = pd.DataFrame()
    for index, data in df.iterrows():
        if data['Uploaded'] == 'No' or data['Uploaded'] == '':
            # Upload to df and embeddings
            add_data(bot_id, data['Title'], data['Heading'], data['Content'])

            # Recreate the df to upload back to the gsheet
            data_dict['Title'] = data['Title']
            data_dict['Heading'] = data['Heading']
            data_dict['Content'] = data['Content']
            data_dict['Uploaded'] = 'Yes'
            print(data_dict)
            data_df = pd.DataFrame([data_dict])
            upload_df = pd.concat([upload_df, data_df])

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

def start_discord_bot(df, document_embeddings):
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

        if message.content.lower().find('@1072338244085227623'.lower()) != -1:
            answer = answer_query_with_context(message.content, df, document_embeddings)
            await message.channel.send(answer)

    client.run(os.getenv('DISCORD_TOKEN'))

def main():

    # title_stack = []
    # openai.api_key = os.getenv('OPENAI_API_KEY')
    # content = get_gitbook_data_in_md_format('https://docs.klimadao.finance', '')
    # # content = "# Introducing KlimaDAO\n\n## The Problem\nIn our market economy, the invisible hand works to create prosperity and individual self-interest prevails. The freedom to produce and consume as we see fit generates value for the economy; value that allows the whole of society to prosper.\nWe generally consider that the market itself is rational, and assume that it values things in a perfect way. We ignore the paradoxes in front of us everyday. Water, a necessity for life is essentially free across (much of) the world; diamonds have no real utility for us, yet in the free market they are priced exorbitantly, excluding all but the world’s richest.\nAccording to the market, Amazon is the world’s most valuable company. But the Amazon Rainforest has no\nuntil its vegetation is cleared for farming, and its trees are stripped of their greenery and extracted as logs.\nIn the past, the market price of a good was determined by the socially necessary labour inputs required to create it. In recent times we have moved to a system where subjectivity and speculation are key driving forces behind prices.\nFor many, the ‘marketplace’ is no longer a place where two people physically exchange goods or services. It is where we buy securities, that we will never touch, that we often do not understand, in order to grow personal wealth.\nValue has become totally detached from the ‘market’.\nSo much so, that when a good or service destroys value, sometimes immeasurably, there is no penalty imposed by the market.\nCarbon dioxide is a greenhouse gas that inhibits our planet’s ability to let heat escape when it gets too stuffy down here. Carbon dioxide’s effect on our global climate is already leading to change in our planet’s most vulnerable ecosystems: it is bleaching coral reefs; melting the permafrost beneath arctic tundra; leading to the desertification of the tropics. There’s no punishment by the market for emitting carbon dioxide.\nWhat we truly value, is not being valued by the market.\n\n## The solution\nClimate change\nthe number one issue of our generation.\nCarbon dioxide knows no borders, nor do the impacts of global warming. The only way to tackle global warming is by mobilising action at the global scale. The market is the best solution we have at our disposal to achieve decarbonisation of our existing economic activity, and to retrospectively capture and store the carbon we have already emitted, at the scale required.\nMarkets are dynamic and more than a place of exchange, they are a manifestation of our culture and our time. So through organisation and co-ordination we have the power to modify them to reflect what we need and want. If we want the market price to be a fair price of what we value, then we need to move the goalposts and force it to work to the parameters we define. A\nmarket should price in carbon.\nTo properly value carbon, we need to fully integrate the\nwith\n, and we need to reward participation for those who participate in the carbon market with value or influence, or both.\nWeb3 is the perfect place to integrate these markets, it is a place where there is sufficient liquidity to have impact at scale, where smart contracts can securely and transparently govern transactions, and where contributions can be fairly incentivised.\n\n### KlimaDAO\nIn acknowledgement that the carbon markets are one of the most powerful and immediately available tools available to us to fight climate change at scale, KlimaDAO was designed.\nKlimaDAO gives individuals and organizations the opportunity to participate directly in the carbon market via its infrastructure and the KLIMA token.\nKlimaDAO infrastructure prioritises accessibility and transparency across the value chain of the carbon markets:\nProject developers can access the infrastructure to immediately find counterparties for their carbon credits.\nThose looking to acquire carbon credits can do so efficiently and securely using Web3 tools.\nTo claim the environmental benefit of any carbon credits, KlimaDAO’s retirement infrastructure enables this to happen with no reliance on intermediaries.\nAnyone who holds tokens, can participate directly in the governance of the system.\nThe system is built on a public blockchain and is fully transparent, for the first time creating a level playing field across the market. The permissionless and interoperable nature of public blockchains enables greater innovation and lower transaction costs across the market.\nUltimately, the KlimaDAO protocol aims to reorient the carbon markets to be more equitable, and ensure that they prioritize the climate. To achieve this, an economy is required, an economy built on top of open, transparent and public infrastructure."
    # print('Gitbook data in md format fetched')
    # add_data_array('Whitepaper', content, title_stack)
    # outputs = create_data_for_docs(title_stack)
    # print('Outputs created for gitbook data')
    # df = final_data_for_openai(outputs)
    # print(df.head)
    # document_embeddings = compute_doc_embeddings(df)
    #
    # print('Embeddings created, sending data to db...')
    # response_after_sending_data = send_to_db(bot_id, bot_description, outputs, document_embeddings)
    #
    #
    #
    # response_after_adding_data = add_data_from_sheet(bot_id, SHEET_ID, SHEET_NAME)
    outputs_from_database, document_embeddings_from_database = retrieve_from_db(bot_id)
    df_from_database = final_data_for_openai(outputs_from_database)

    start_discord_bot(df_from_database, document_embeddings_from_database)



if __name__ == '__main__':
    main()