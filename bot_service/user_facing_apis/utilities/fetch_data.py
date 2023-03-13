
import discord
from transformers import GPT2TokenizerFast
import sys

import numpy as np
from github import Github
from dotenv import dotenv_values
import time
import pyparsing as pp
import openai
import pandas as pd
import tiktoken
from nltk.tokenize import sent_tokenize
import nltk
import urllib
import requests
import json
import ssl
from itertools import islice

from utilities.scrapers.gitbook_scraper import *
from utilities.scrapers.pdf_parse_seq import *

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

nltk.download('punkt')
config = dotenv_values("../.env") 

openai.api_key = config['OPENAI_API_KEY']
tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
COMPLETIONS_MODEL = "text-davinci-003"
EMBEDDING_MODEL = "text-embedding-ada-002"
MAX_SECTION_LEN = 500
SEPARATOR = "\n* "
ENCODING = "cl100k_base"
min_token_limit = 10
EMBEDDING_COST = 0.0004
COMPLETIONS_COST = 0.03

encoding = tiktoken.get_encoding(ENCODING)
separator_len = len(encoding.encode(SEPARATOR))

# f"Context separator contains {separator_len} tokens"


COMPLETIONS_API_PARAMS = {
    # We use temperature of 0.0 because it gives the most predictable, factual answer.
    "temperature": 0.0,
    "max_tokens": 300,
    "model": COMPLETIONS_MODEL,
}


# Functions to fetch data


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

def read_docs(github_repo):
    g = Github(config['GITHUB_ACCESS_TOKEN'])
    repo = g.get_repo(github_repo)
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
            if file_content.path.find('orchestrator') == -1: ## remove this line later
                continue ## remove this line later
            if file_content.name.endswith('md') or file_content.name.endswith('mdx'):
                file_contents = repo.get_contents(file_content.path)
                title = pp.AtLineStart(pp.Word("#")) + pp.rest_of_line
                sample = file_contents.decoded_content.decode()
                sample = cleanup_data(sample)

                title_stack.append([0, 'start_of_file'])
                if sample.split('\n')[0] == '---':
                    title_stack[-1].append('')
                    title_stack[-1].append(file_content.path)
                    title_stack.append([1, sample.split('\n')[1].split(':')[1].lstrip()])
                    sample = sample.split('---')[2]

                last_end = 0
                for t, start, end in title.scan_string(sample):
                    # save content since last title in the last item in title_stack
                    title_stack[-1].append(sample[last_end:start].lstrip("\n"))
                    title_stack[-1].append(file_content.path)

                    # add a new entry to title_stack
                    marker, title_content = t
                    level = len(marker)
                    title_stack.append([level, title_content.lstrip()])

                    # update last_end to the end of the current match
                    last_end = end

                # add trailing text to the final parsed title
                title_stack[-1].append(sample[last_end:])
                title_stack[-1].append(file_content.path)
    return title_stack

def create_data_for_docs(protocol_title, title_stack):
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
        title = protocol_title + " - " + dir_elements[0]
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
    # outputs += [(title, h, c, t) if t<max_len
    #             else (title, h, reduce_long(c, max_len), count_tokens(reduce_long(c,max_len)))
    #             for title, h, c, t in zip(ntitles, nheadings, ncontents, ncontent_ntokens)]
    for title, h, c, t in zip(ntitles, nheadings, ncontents, ncontent_ntokens):
        if (t<max_len and t>min_token_limit):
            outputs += [(title,h,c,t)]
        elif(t>=max_len):
            outputs += [(title, h, reduce_long(c, max_len), count_tokens(reduce_long(c,max_len)))]
    return outputs

def final_data_for_openai(outputs):
    res = []
    res += outputs
    df = pd.DataFrame(res, columns=["title", "heading", "content", "tokens"])
    # df = df[df.tokens>10] # was initially 40 (need to ask Abhishek why)
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

def get_embedding(text: str, model: str = EMBEDDING_MODEL):
    time.sleep(7)
    result = openai.Embedding.create(
        model=model,
        input=text
    )
    return result["data"][0]["embedding"], result["usage"]["total_tokens"]

def compute_doc_embeddings(df: pd.DataFrame):
    """
    Create an embedding for each row in the dataframe using the OpenAI Embeddings API.
    Return a dictionary that maps between each embedding vector and the index of the row that it corresponds to.
    """
    print('hello boys')
    embedding_dict = {}
    total_tokens_used = 0
    for idx, r in df.iterrows():
        embedding, tokens = get_embedding(r.content)
        embedding_dict[idx] = embedding
        total_tokens_used = total_tokens_used + tokens
    cost_incurred = total_tokens_used * EMBEDDING_COST / 1000
    print(cost_incurred)
    return embedding_dict, cost_incurred

def read_from_github(protocol_title, github_link):
    github_repo = github_link.partition("github.com/")[2]
    print(github_repo)
    title_stack = read_docs(github_repo)
    outputs = create_data_for_docs(protocol_title, title_stack)
    print(outputs)
    df = final_data_for_openai(outputs)
    print(df.head)
    document_embeddings, cost_incurred = compute_doc_embeddings(df)
    print(len(df), " rows in the data.")
    return outputs, document_embeddings, cost_incurred

def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content

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

def get_data_from_gitbook(gitbook_data_type, gitbook_link):
    content = get_gitbook_data_in_md_format(gitbook_link, '')
    print('Gitbook data in md format fetched')
    title_stack = add_data_array(gitbook_data_type, content)
    outputs = create_data_for_docs(title_stack)
    print('Outputs created for gitbook data')
    df = final_data_for_openai(outputs)
    print(df.head)
    document_embeddings, cost_incurred = compute_doc_embeddings(df)
    print('Embeddings created, sending data to db...')
    return outputs, document_embeddings, cost_incurred

def get_whitepaper_data(type, document):
    content = convert_to_md_format(document)
    title_stack = add_data_array(type, content)
    outputs = create_data_for_docs(title_stack)
    print('Outputs created for whitepaper data')
    df = final_data_for_openai(outputs)
    print(df.head)
    document_embeddings, cost_incurred = compute_doc_embeddings(df)
    print('Embeddings created, sending data to db...')
    return outputs, df, document_embeddings, cost_incurred



# Functions to help answer queries


def vector_similarity(x: list[float], y: list[float]) -> float:
    """
    Returns the similarity between two vectors.

    Because OpenAI Embeddings are normalized to length 1, the cosine similarity is the same as the dot product.
    """
    return np.dot(np.array(x), np.array(y))


def order_document_sections_by_query_similarity(query_embedding: list[float],
                                                 contexts: dict[tuple[str, str], np.array]):
    """
    Find the query embedding for the supplied query, and compare it against all of the pre-calculated document embeddings
    to find the most relevant sections.
    Return the list of document sections, sorted by relevance in descending order.
    """
    document_similarities = sorted([
        (vector_similarity(query_embedding, doc_embedding), doc_index) for doc_index, doc_embedding in contexts.items()
    ], reverse=True)

    return document_similarities


def construct_prompt(question: str, question_embedding: list[float], context_embeddings: dict, df: pd.DataFrame):
    """
    Fetch relevant
    """
    most_relevant_document_sections = order_document_sections_by_query_similarity(question_embedding,
                                                                                   context_embeddings)

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
        question_embedding: list,
        df: pd.DataFrame,
        document_embeddings: dict[tuple[str, str], np.array],
        show_prompt: bool = False
):
    prompt = construct_prompt(
        query,
        question_embedding,
        document_embeddings,
        df
    )
    if show_prompt:
        print(prompt)

    response = openai.Completion.create(
        prompt=prompt,
        **COMPLETIONS_API_PARAMS
    )
    answer_cost = response["usage"]["total_tokens"] * COMPLETIONS_COST / 1000
    return response["choices"][0]["text"].strip(" \n"), answer_cost