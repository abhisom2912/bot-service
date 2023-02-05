import requests
from bs4 import BeautifulSoup
from markdownify import markdownify
page = requests.get("https://layerzero.gitbook.io/docs/faq/future-proof-architecture")
soup = BeautifulSoup(page.content, 'html.parser')
html = list(soup.children)[2]
body = list(html.children)[3]
p = list(body.children)[1]
print(p.get_text())
# data = markdownify(body, heading_style="ATX")
# print(data)
# list(body.children)
# print(body)