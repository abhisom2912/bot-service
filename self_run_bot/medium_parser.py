import re

import requests
from bs4 import BeautifulSoup
from datetime import datetime

# script to scrape data from a user's Medium articles

def remove_all(s, start_ch, end_ch):
    previous_ind = 0
    length = len(s)
    orig_s = s
    final_string = s
    while 1:
        try:
            ind = s.index(start_ch)
            start_index = ind + previous_ind
            s = s[ind + len(start_ch):length]
            previous_ind = previous_ind + ind + len(start_ch)

            ind = s.index(end_ch)
            end_index = ind + previous_ind + len(end_ch)
            s = s[ind + len(end_ch):length]
            previous_ind = previous_ind + ind + len(end_ch)

            replace_string = orig_s[start_index: end_index]
            final_string = final_string.replace(replace_string, '')
        except ValueError:
            break
    return final_string

# scraping the Medium articles published by a user (using their username)
def get_medium_data(username, valid_articles_duration_days):
    url = "https://api.rss2json.com/v1/api.json?rss_url=https://medium.com/feed/" + username

    response = requests.request("GET", url)
    response_json = response.json()
    items = response_json['items']

    title_stack = []
    for item in items: # for every article published by the user in the specified duration
        title = item['title']
        link = item['guid']
        pub_date = item['pubDate']
        date_p = datetime.strptime(pub_date, '%Y-%m-%d %H:%M:%S')
        if (datetime.now() - date_p).days <= valid_articles_duration_days:
            content = item['content']
            final_content = '<h1>' + title + '</h1>' + content
            final_content = remove_all(final_content, "<figure>", "</figure>")
            title_stack = title_stack + convert_to_stack(final_content, link)
    return title_stack

# converting the article contents into our desired format
def convert_to_stack(final_content, link):
    title_stack = []
    soup = BeautifulSoup(final_content, 'html.parser')
    headings = soup.find_all(re.compile("^h[1-6]$"))
    i = 0
    while i < len(headings) - 1:
        header_level = int(re.findall("h[1-6]", str(headings[i]))[0].split('h')[1])
        text_btw = find_between(str(soup), str(headings[i]), str(headings[i + 1]))
        soup1 = BeautifulSoup(text_btw, 'html.parser')
        content_text = soup1.get_text()
        title_stack.append([header_level, headings[i].get_text(), content_text, link])
        i = i + 1
    header_level = int(re.findall("h[1-6]", str(headings[i]))[0].split('h')[1])
    text_btw = find_last(str(soup), str(headings[i]))
    soup1 = BeautifulSoup(text_btw, 'html.parser')
    content_text = soup1.get_text()
    title_stack.append([header_level, headings[i].get_text(), content_text, link]) # returning a list where each element contains the header level, the heading, its corresponding text, and the URL of the article
    return title_stack


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def find_last(s, first):
    try:
        start = s.index(first) + len(first)
        end = len(s)
        return s[start:end]
    except ValueError:
        return ""


if __name__ == '__main__':
    title_stack = get_medium_data("@revert_finance", 35)
