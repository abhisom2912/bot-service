
import discord
from transformers import GPT2TokenizerFast

import numpy as np
from github import Github
import os
import time
import pyparsing as pp
import openai
import pandas as pd
import tiktoken
from nltk.tokenize import sent_tokenize
from typing import List
from typing import Dict
from typing import Tuple
import nltk
from pdf_parse_seq import *

nltk.download('punkt')

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
        i = i+1
        end_index = index_array[i]
        orig_string = s[start_index:end_index]
        replaced_string = orig_string.replace('#', '--')
        s = s.replace(orig_string, replaced_string)
        i = i+1
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

def read_docs() -> []:
    g = Github(os.getenv('GITTOKEN'))
    repo = g.get_repo('abhisom2912/nft-drop-starter-project')
    title_stack=[]
    contents = repo.get_contents("")
    while contents:
        try:
            file_content = contents.pop(0)
        except Exception:
            pass
        if file_content.type == "dir":
            contents.extend(repo.get_contents(file_content.path))
        else:
            if file_content.path.find('Dfyn V2') == -1:
                continue
            if file_content.name.endswith('md') or file_content.name.endswith('mdx'):
                file_contents = repo.get_contents(file_content.path)
                sample = file_contents.decoded_content.decode()
                add_data_array(file_content.path, sample, title_stack)
    return title_stack

def create_data_for_docs(title_stack) -> []:
    heads = {}
    max_level = 0
    nheadings, ncontents, ntitles = [], [], []
    outputs = []
    max_len = 1500
    s1 = '<Section'
    s2 = '</Section>'

    for level, header, content, dir in title_stack:
        dir_elements = []
        final_header = header
        dir_elements_temp = dir.split('/')
        for dir in dir_elements_temp:
            dir_split = dir.rsplit(" ", 1)[0]
            try:
                extension = '.' + dir.rsplit(" ", 1)[1].split('.')[1]
            except IndexError:
                extension = ''
            final_dir = dir_split + extension
            dir_elements.append(final_dir)
        element_len = 1
        dir_header = ''
        sub = 1
        title = 'Dfyn V2' + " - " + dir_elements[0]
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

def final_data_for_openai(outputs):
    res = []
    res += outputs
    df = pd.DataFrame(res, columns=["title", "heading", "content", "tokens"])
    df = df[df.tokens>40]
    df = df.drop_duplicates(['title','heading'])
    df = df.reset_index().drop('index',axis=1) # reset index
    return df

def add_data_array(file_path, content, title_stack):
    title = pp.AtLineStart(pp.Word("#")) + pp.rest_of_line
    content = cleanup_data(content)
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

def add_whitepaper_data(document, title_stack):
    content = convert_to_md_format(document)
    add_data_array('Whitepaper', content, title_stack)

def get_embedding(text: str, model: str=EMBEDDING_MODEL) -> List[float]:
    time.sleep(3)
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

def initialize():
    document = '/Users/abhisheksomani/Downloads/Dfyn_V2_Whitepaper-pages-4-15.pdf'
    title_stack = read_docs()
    if document != '':
        add_whitepaper_data(document, title_stack)
    outputs = create_data_for_docs(title_stack)
    df = final_data_for_openai(outputs)
    print(df.head)
    df = df.set_index(["title", "heading"])
    document_embeddings = compute_doc_embeddings(df)
    print("{len(df)} rows in the data.")
    return df, document_embeddings

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

        if message.content.lower().find('@1064872402003169312'.lower()) != -1:
            answer = answer_query_with_context(message.content, df, document_embeddings)
            await message.channel.send(answer)

    client.run(os.getenv('DISCORD_TOKEN'))


def main():
    df, document_embeddings  = initialize()
    start_discord_bot(df, document_embeddings)

if __name__ == '__main__':
    main()