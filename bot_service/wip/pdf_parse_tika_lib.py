import json
import pdfplumber
import re
import tika
from tika import parser


def main():
    parsed_pdf = parser.from_file('/Users/abhisheksomani/Downloads/Dfyn_V2_Whitepaper.pdf')
    print(parsed_pdf['content'])
    for my_key, my_value in parsed_pdf["metadata"].items():
        print(my_key)
        print('\t' + my_value + '\n')

    my_content = parsed_pdf['content']
    print(my_content)
    # print(parsedPDF['metadata'])
    # print(parsedPDF)


if __name__ == '__main__':
    main()