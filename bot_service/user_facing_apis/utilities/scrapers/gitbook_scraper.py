import requests
from bs4 import BeautifulSoup
import re
import httplib2

# script to scrape all the pages from your Gitbook documentation using just your docs link

BASE_URL = ''  # for eg. https://v1.docs.routerprotocol.com/
FIRST_PAGE_PATH = ''  # for eg. whitepaper/abstract

def get_all_page_urls(base_url, first_url):
    all_page_urls = []
    base_page = base_url + first_url
    all_page_urls.append(base_page)
    page = requests.get(base_page)
    soup = BeautifulSoup(page.content, 'html.parser')
    next_available = False
    for link in soup.find_all('a', href=True):
        if 'Next' in link.get_text():  # if the keyword "Next" is available in the page
            remaining_url = link['href']
            next_available = True

    while next_available:
        next_available = False
        page_url = base_url + remaining_url
        all_page_urls.append(page_url)
        page = requests.get(page_url)
        soup = BeautifulSoup(page.content, 'html.parser')
        for link in soup.find_all('a', href=True):
            if 'Next' in link.get_text():
                remaining_url = link['href']
                next_available = True

    return all_page_urls


def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

def find_last( s, first ):
    try:
        start = s.index( first ) + len( first )
        end = len(s)
        return s[start:end]
    except ValueError:
        return ""

# scraping the Gitbook data
def get_gitbook_data(base_url, first_url, gitbook_data_type):
    title_stack = []

    # getting all the paths in the user's documentation using the base URL and the path of the first page
    all_page_urls = get_all_page_urls(base_url, first_url)

    for page_url in all_page_urls: # for every page in the user's documentation
        page = requests.get(page_url)

        # parsing the page using the BeautifulSoup library
        soup = BeautifulSoup(page.content, 'html.parser')

        html = list(soup.children)[2]
        body = list(html.children)[3]
        p = list(body.children)[1]

        # getting all the headings in the page
        headings = p.find_all(re.compile("^h[1-6]$"))

        if len(headings) == 0:
            continue

        i = 0
        while i < len(headings) - 1:
            header_level = int(re.findall("h[1-6]", str(headings[i]))[0].split('h')[1])
            
            # scraping the text between two headings (to make it a part of key-value pair between headings and its corresponding text)
            text_btw = find_between(str(p), str(headings[i]), str(headings[i + 1]))
            soup1 = BeautifulSoup(text_btw, 'html.parser')
            spans = soup1.find_all('span', {"data-key":""})
            content_text = ''
            for span in spans:
                content_text = content_text + span.get_text() + '\n'
            title_stack.append([header_level, headings[i].get_text(), content_text, page_url])
            i = i + 1

        header_level = int(re.findall("h[1-6]", str(headings[i]))[0].split('h')[1])
        text_btw = find_last(str(p), str(headings[i]))
        soup1 = BeautifulSoup(text_btw, 'html.parser')
        spans = soup1.find_all('span', {"data-key":""})
        content_text = ''
        for span in spans:
            content_text = content_text + span.get_text() + '\n'
        title_stack.append([header_level, headings[i].get_text(), content_text, page_url]) # returning a list where each element contains the header level, the heading, its corresponding text, and the URL of the page
    print(title_stack[0])
    return title_stack

def main():
    output = get_gitbook_data(BASE_URL, FIRST_PAGE_PATH)
    print(output)

if __name__ == '__main__':
    main()

