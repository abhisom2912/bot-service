from asgiref.sync import sync_to_async
import discord
from transformers import GPT2TokenizerFast
import sys
from github import Github
from dotenv import dotenv_values
import time
import pyparsing as pp
import openai
import pandas as pd
import tiktoken
from nltk.tokenize import sent_tokenize
import nltk
import requests
import json
import multiprocessing
import ssl

from pdf_parse_seq import *
from gitbook_scraper import *
from medium_parser import *

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.download('punkt')
config = dotenv_values(".env")

openai.api_key = config['OPENAI_API_KEY']

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
COMPLETIONS_MODEL = "text-davinci-003"
EMBEDDING_MODEL = "text-embedding-ada-002"
MAX_SECTION_LEN = 500
SEPARATOR = "\n* "
ENCODING = "cl100k_base"
min_token_limit = 10

encoding = tiktoken.get_encoding(ENCODING)
separator_len = len(encoding.encode(SEPARATOR))

COMPLETIONS_API_PARAMS = {
    # We use temperature of 0.0 because it gives the most predictable, factual answer.
    "temperature": 0.0,
    "max_tokens": 300,
    "model": COMPLETIONS_MODEL,
}

def find_all(s, ch):
    previous_ind = 0
    array = []
    length = len(s)
    while 1:
        try:
            ind = s.index(ch)
            array.append(ind + previous_ind)
            s = s[ind + len(ch):length]
            previous_ind = previous_ind + ind + len(ch)
        except ValueError:
            break
    return array


def remove_unwanted_char(s):
    code_separator = "```"
    index_array = find_all(s, code_separator)
    i = 0
    while i < len(index_array):
        start_index = index_array[i]
        i = i + 1
        end_index = index_array[i]
        orig_string = s[start_index:end_index]
        replaced_string = orig_string.replace('#', '--')
        s = s.replace(orig_string, replaced_string)
        i = i + 1
    return s


def get_needed_hash(s):
    s_array = s.split("\n")
    i = len(s_array) - 1
    req_no_of_hash = 2
    while i > 0:
        if s_array[i].find("#") != -1:
            req_no_of_hash = s_array[i].count('#') + 1
            break
        i = i - 1
    no_hash = 0
    hash_string = ''
    while no_hash < req_no_of_hash:
        hash_string = hash_string + '#'
        no_hash = no_hash + 1
    return hash_string


def cleanup_data(s):
    s = remove_unwanted_char(s)
    s = s.replace('<details>', '')
    s = s.replace('</details>', '')
    s = s.replace('</b></summary>', '')
    # hash_string = get_needed_hash(s[0:s.find('<summary><b>')])
    hash_string = ''
    s = s.replace('<summary><b>', hash_string)
    return s

def clean_content(content):
    s1 = '<Section'
    s2 = '</Section>'
    remove_content = find_between(content, s1, s2)
    content = content.replace(remove_content,'').replace(s1, '').replace(s2, '')
    return content

def read_docs(github_repo):
    doc_file_path = 'docs/'
    g = Github(config['GITHUB_ACCESS_TOKEN'])
    repo = g.get_repo(github_repo)
    title_stack = []
    contents = repo.get_contents("")
    file_content = ''
    while contents:
        try:
            file_content = contents.pop(0)
        except Exception:
            pass
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        else:
            if file_content.path.find(doc_file_path) == -1 or file_content.path.find('crosstalk') == -1:  ## remove this line later
                continue  ## remove this line later
            if file_content.name.endswith('md') or file_content.name.endswith('mdx'):
                file_contents = repo.get_contents(file_content.path)
                title = pp.AtLineStart(pp.Word("#")) + pp.rest_of_line
                sample = file_contents.decoded_content.decode()
                sample = cleanup_data(sample)

                title_stack.append([0, 'start_of_file'])
                if sample.split('\n')[0] == '---':
                    title_stack[-1].append('')
                    title_stack[-1].append(file_content.path.replace(doc_file_path, ''))
                    title_stack.append([1, sample.split('\n')[1].split(':')[1].lstrip()])
                    sample = sample.split('---')[2]

                last_end = 0
                for t, start, end in title.scan_string(sample):
                    # save content since last title in the last item in title_stack
                    title_stack[-1].append(clean_content(sample[last_end:start].lstrip("\n")))
                    title_stack[-1].append(file_content.path.replace(doc_file_path, ''))

                    # add a new entry to title_stack
                    marker, title_content = t
                    level = len(marker)
                    title_stack.append([level, title_content.lstrip()])

                    # update last_end to the end of the current match
                    last_end = end

                # add trailing text to the final parsed title
                title_stack[-1].append(clean_content(sample[last_end:]))
                title_stack[-1].append(file_content.path.replace(doc_file_path, ''))
    return title_stack


def create_data_for_docs(protocol_title, title_stack, doc_link, doc_type):
    heads = {}
    max_level = 0
    nheadings, ncontents, ntitles, nlinks = [], [], [], []
    outputs = []
    max_len = 1500


    for level, header, content, dir in title_stack:
        final_header = header
        dir_header = ''

        if doc_type == 'whitepaper':
            content_link = doc_link
            title = protocol_title + " - whitepaper"
        elif doc_type == 'gitbook':
            content_link =  dir
            title = protocol_title + " - whitepaper"
            dir_elements = dir.replace('https://', '').split('/')
            element_len = 1
            while element_len < len(dir_elements) - 1:
                dir_header += dir_elements[element_len].replace('-', ' ') + ': '
                element_len += 1
        elif doc_type == 'medium':
            content_link = dir
            title = protocol_title + " - articles"

        else:
            element_len = 1
            dir_elements = dir.split('/')
            content_link = doc_link + '/' + dir_elements[0]
            sub = 1
            title = protocol_title + " - " + dir_elements[0]
            if dir_elements[len(dir_elements) - sub].find('README') != -1:
                sub = sub + 1
            while element_len < len(dir_elements) - sub:
                dir_header = dir_header + dir_elements[element_len] + ': '
                element_len = element_len + 1

            element_len = 1
            while element_len < len(dir_elements) - sub + 1:
                if dir_elements[element_len].find('.md'):
                    link = dir_elements[element_len].replace('.mdx', '').replace('.md', '')
                content_link = content_link + '/' + link
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
            i = i - 1
        final_header = dir_header + final_header
        if final_header.find('start_of_file') == -1:
            if content.strip() == '':
                continue
            nheadings.append(final_header.strip())
            ncontents.append(content)
            ntitles.append(title)
            nlinks.append(content_link)


    ncontent_ntokens = [
        count_tokens(c)
        + 3
        + count_tokens(" ".join(h.split(" ")[1:-1]))
        - (1 if len(c) == 0 else 0)
        for h, c in zip(nheadings, ncontents)
    ]
    for title, h, c, t, l in zip(ntitles, nheadings, ncontents, ncontent_ntokens, nlinks):
        if (t < max_len and t > min_token_limit):
            outputs += [(title, h, c, t, l)]
        elif (t >= max_len):
            outputs += [(title, h, reduce_long(c, max_len), count_tokens(reduce_long(c, max_len)), l)]
    return outputs


def final_data_for_openai(outputs):
    res = []
    res += outputs
    df = pd.DataFrame(res, columns=["title", "heading", "content", "tokens", "link"])
    # df = df[df.tokens>10] # was initially 40 (need to ask Abhishek why)
    df = df.drop_duplicates(['title', 'heading'])
    df = df.reset_index().drop('index', axis=1)  # reset index
    df = df.set_index(["title", "heading"])
    return df


def count_tokens(text: str) -> int:
    """count the number of tokens in a string"""
    return len(tokenizer.encode(text))


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.rindex(last, start)
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


def get_embedding(text: str, sleep_time, model: str = EMBEDDING_MODEL) -> list[float]:
    time.sleep(sleep_time)
    result = openai.Embedding.create(
        model=model,
        input=text
    )
    return result["data"][0]["embedding"]


def compute_doc_embeddings(df: pd.DataFrame) -> dict[tuple[str, str], list[float]]:
    """
    Create an embedding for each row in the dataframe using the OpenAI Embeddings API.

    Return a dictionary that maps between each embedding vector and the index of the row that it corresponds to.
    """
    return {
        idx: get_embedding(r.content, 7) for idx, r in df.iterrows()
    }


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


def vector_similarity(x: list[float], y: list[float]) -> float:
    """
    Returns the similarity between two vectors.

    Because OpenAI Embeddings are normalized to length 1, the cosine similarity is the same as the dot product.
    """
    return np.dot(np.array(x), np.array(y))


def order_document_sections_by_query_similarity(query: str, contexts: dict[tuple[str, str], np.array]) -> list[
    tuple[float, tuple[str, str]]]:
    """
    Find the query embedding for the supplied query, and compare it against all of the pre-calculated document embeddings
    to find the most relevant sections.

    Return the list of document sections, sorted by relevance in descending order.
    """
    query_embedding = get_embedding(query, 0)

    document_similarities = sorted([
        (vector_similarity(query_embedding, doc_embedding), doc_index) for doc_index, doc_embedding in contexts.items()
    ], reverse=True)

    return document_similarities


def construct_prompt(question: str, context_embeddings: dict, df: pd.DataFrame):
    """
    Fetch relevant
    """
    most_relevant_document_sections = order_document_sections_by_query_similarity(question, context_embeddings)

    chosen_sections = []
    chosen_sections_len = 0
    chosen_sections_indexes_string = []
    chosen_sections_indexes = []

    for _, section_index in most_relevant_document_sections:
        # Add contexts until we run out of space.
        document_section = df.loc[section_index]

        chosen_sections_len += document_section.tokens + separator_len
        if chosen_sections_len > MAX_SECTION_LEN:
            break

        chosen_sections.append(SEPARATOR + document_section.content.replace("\n", " "))
        chosen_sections_indexes_string.append(str(section_index))
        chosen_sections_indexes.append(section_index)

    # Useful diagnostic information
    print("Selected ", len(chosen_sections), " document sections:")
    print("\n".join(chosen_sections_indexes_string))

    header = """Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the text below, say "Sorry, I am not sure of this. Please contact one of the admins."\n\nContext:\n"""

    return header + "".join(chosen_sections) + "\n\n Q: " + question + "\n A:", chosen_sections_indexes


def answer_query_with_context(
        query: str,
        df: pd.DataFrame,
        document_embeddings: dict[tuple[str, str], np.array],
        show_prompt: bool = False
):
    prompt, chosen_sections_indexes = construct_prompt(
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

    links = []
    for section_index in chosen_sections_indexes:
        document_section = df.loc[section_index]
        link = document_section['link']
        if link != '' and not (link in links):
            links.append(link)
        if len(links) >= 2:
            break

    return response["choices"][0]["text"].strip(" \n"), links


def read_from_github(protocol_title, github_repo, github_doc_link):
    title_stack = read_docs(github_repo)
    outputs = create_data_for_docs(protocol_title, title_stack, github_doc_link, 'github')
    df = final_data_for_openai(outputs)
    print(df.head)
    document_embeddings = compute_doc_embeddings(df)
    print(len(df), " rows in the data.")
    return outputs, df, document_embeddings


def get_data_from_gitbook(gitbook_link, protocol_title):
    title_stack = get_gitbook_data(gitbook_link, '')
    outputs = create_data_for_docs(protocol_title, title_stack, '', 'gitbook')
    print('Outputs created for gitbook data')
    df = final_data_for_openai(outputs)
    print(df.head)
    document_embeddings = compute_doc_embeddings(df)
    print('Embeddings created, sending data to db...')
    return outputs, df, document_embeddings

def get_data_from_medium(username, valid_articles_duration_days, protocol_title):
    title_stack = get_medium_data(username, valid_articles_duration_days)
    outputs = create_data_for_docs(protocol_title, title_stack, '', 'medium')
    print('Outputs created for gitbook data')
    df = final_data_for_openai(outputs)
    print(df.head)
    document_embeddings = compute_doc_embeddings(df)
    print('Embeddings created, sending data to db...')
    return outputs, df, document_embeddings

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
        if (t < max_len and t > min_token_limit):
            outputs += [(title, h, c, t)]
        elif (t >= max_len):
            outputs += [(title, h, reduce_long(c, max_len), count_tokens(reduce_long(c, max_len)))]

    return outputs


class DiscordBot(multiprocessing.Process):
    def __init__(self, df, document_embeddings):
        super(DiscordBot, self).__init__()
        self.df = df
        self.document_embeddings = document_embeddings

    def run(self):
        intents = discord.Intents.default()
        intents.message_content = True
        client = discord.Client(intents=intents)

        @client.event
        async def on_ready():
            print('We have logged in as {0.user}'.format(client))

        @client.event
        async def on_message(message):
            if message.author == client.user:
                return

            if message.content.lower().find('@1064872402003169312'.lower()) != -1 or message.clean_content.lower().find('@jarvis') != -1:
                question = message.content.replace('<@1064872402003169312> ', '')
                answer, links = await sync_to_async(answer_query_with_context)(question, self.df, self.document_embeddings)
                # answer, links = answer_query_with_context(question, self.df, self.document_embeddings)
                link_number = 1
                link_text = ''
                for link in links:
                    if link_number == 1:
                        link_text = ' [Link' + str(link_number) + '](' + link + ')'
                    else:
                        link_text += ', [Link' + str(link_number) + '](' + link + ')'
                    link_number += 1
                embedVar = discord.Embed(description=answer)
                if link_text != '' and answer.find('Sorry, I am not sure of this. Please contact one of the admins') == -1:
                    embedVar.add_field(name="Relevant links", value="To read more, check out the following links -" + link_text, inline=False)
                await message.reply(embed = embedVar)

        client.run(config['DISCORD_TOKEN'])


def untuplify_dict_keys(mapping):
    string_keys = {json.dumps(k): v for k, v in mapping.items()}
    return string_keys


def tuplify_dict_keys(string):
    mapping = string
    return {tuple(json.loads(k)): v for k, v in mapping.items()}


def send_to_db(protocol_title, doc_type, outputs, document_embeddings):
    data_to_post = {"protocol_title": protocol_title, "document_type": doc_type, "data": outputs,
                    "embeddings": untuplify_dict_keys(document_embeddings)}
    response = requests.post(config['BASE_API_URL'] + "document/", json=data_to_post)
    return response


def retrieve_from_db():
    response = requests.get(config['BASE_API_URL'] + "document/")
    json_response = response.json()
    outputs = []
    document_embeddings = {}
    for document in json_response:
        outputs.extend(document['data'])
        document_embeddings.update(document['embeddings'])
    document_embeddings = tuplify_dict_keys(document_embeddings)
    return outputs, document_embeddings


def delete_data_in_db(protocol_title, _type):
    requests.delete(config['BASE_API_URL'] + "document/" + protocol_title + "/" + _type)


def add_data_array(file_path, content):
    title_stack = []
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
    return title_stack


def get_whitepaper_data(protocol_title, type, document, whitepaper_link):
    content = convert_to_md_format(document)
    title_stack = add_data_array(type, content)
    outputs = create_data_for_docs(protocol_title, title_stack, whitepaper_link, 'whitepaper')
    print('Outputs created for whitepaper data')
    df = final_data_for_openai(outputs)
    print(df.head)
    document_embeddings = compute_doc_embeddings(df)
    print('Embeddings created, sending data to db...')
    return outputs, df, document_embeddings


def read_command_line_params():
    arguments = {}
    n = len(sys.argv)
    for i in range(1, n):
        argument = sys.argv[i].split('=')
        arguments[argument[0]] = argument[1]
    return arguments


def main():
    # Parameters for the command line
    # data_id - bot id for which the data needs to be uploaded
    # reset_bot | first_start - in case you want to rerun the initial data upload in the db
    # protocol_title - protocol name
    # read_from_github - true/false based on if data needs to be read by github
    # github_repo - mandatory field if read_from_github is true
    # github_doc_link - base link for github
    # read_from_whitepaper - true/false based on if data needs to be read from whitepaper
    # whitepaper_path - mandatory field if read_from_whitepaper is true
    arguments = read_command_line_params()

    if (arguments.get('reset_bot') is not None and arguments['reset_bot'].lower() == 'true') or (
            arguments.get('first_start') is not None and
            arguments['first_start'].lower() == 'true'):

        if arguments.get('protocol_title') is None:
            raise Exception("Please provide protocol name and document type for adding")

        protocol_title = arguments['protocol_title'].lower()
        if arguments.get('read_from_whitepaper') is not None and arguments['read_from_whitepaper'].lower() == 'true':
            delete_data_in_db(protocol_title, 'whitepaper')
            try:
                whitepaper_path = arguments['whitepaper_path']
            except KeyError:
                raise Exception("Whitepaper path not provided, while read from whitepaper is true")

            whitepaper_link = ''
            if arguments.get('whitepaper_link') is not None:
                whitepaper_link = arguments['whitepaper_link']
            outputs, df, document_embeddings = get_whitepaper_data(protocol_title, 'Whitepaper', whitepaper_path, whitepaper_link)
            if len(outputs) > 0:
                send_to_db(protocol_title, 'whitepaper', outputs, document_embeddings)

        if arguments.get('read_from_gitbook_link') is not None and arguments['read_from_gitbook_link'].lower() == 'true':
            try:
                gitbook_link = arguments['gitbook_link']
            except KeyError:
                raise Exception("Gitbook link not provided, while read from gitbook is true")
            outputs, df, document_embeddings = get_data_from_gitbook(gitbook_link, protocol_title)
            if len(outputs) > 0:
                send_to_db(protocol_title, 'gitbook', outputs, document_embeddings)

        if arguments.get('read_from_github') is not None and arguments['read_from_github'].lower() == 'true':
            delete_data_in_db(protocol_title, 'github')
            if arguments.get('github_repo') is None:
                raise Exception("Github link not provided, while read from github is true")
            elif arguments.get('github_doc_link') is None:
                raise Exception("Github doc link not provided, while read from github is true")
            else:
                github_repo = arguments['github_repo']
                outputs, df, document_embeddings = read_from_github(protocol_title, github_repo, arguments['github_doc_link'])
                if len(outputs) > 0:
                    send_to_db(protocol_title, 'github', outputs, document_embeddings)

        if arguments.get('read_from_medium') is not None and arguments['read_from_medium'].lower() == 'true':
            duration = 10000 if arguments.get('valid_articles_duration_days') is None else arguments.get('valid_articles_duration_days')
            if arguments.get('medium_username') is None:
                raise Exception("Medium username not provided, while read from Medium is true")
            outputs, df, document_embeddings = get_data_from_medium(arguments.get('medium_username'), duration, protocol_title)
            if len(outputs) > 0:
                send_to_db(protocol_title, 'github', outputs, document_embeddings)

    outputs_from_database, document_embeddings_from_database = retrieve_from_db()
    df_from_database = final_data_for_openai(outputs_from_database)
    p = DiscordBot(df_from_database, document_embeddings_from_database)
    p.start()


if __name__ == '__main__':
    main()
