from operator import itemgetter
import fitz
import re
import numpy as np


BOLD_FLAGS = 16

def fonts(doc, granularity=False):
    """Extracts fonts and their usage in PDF documents.
    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param granularity: also use 'font', 'flags' and 'color' to discriminate text
    :type granularity: bool
    :rtype: [(font_size, count), (font_size, count}], dict
    :return: most used fonts sorted by count, font style information
    """
    styles = {}
    font_counts = {}

    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if granularity:
                            identifier = "{0}_{1}_{2}_{3}".format(s['size'], s['flags'], s['font'], s['color'])
                            styles[identifier] = {'size': s['size'], 'flags': s['flags'], 'font': s['font'],
                                                  'color': s['color']}
                        else:
                            identifier = "{0}".format(s['size'])
                            styles[identifier] = {'size': s['size'], 'font': s['font']}

                        font_counts[identifier] = font_counts.get(identifier, 0) + 1  # count the fonts usage

    font_counts = sorted(font_counts.items(), key=itemgetter(1), reverse=True)

    if len(font_counts) < 1:
        raise ValueError("Zero discriminating fonts found!")

    return font_counts, styles

def get_para_length(doc):
    length = []
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        length.append(s['bbox'][2] - s['bbox'][0])

    return np.percentile(length, 90)

def font_tags(font_counts, styles):
    """Returns dictionary with font sizes as keys and tags as value.
    :param font_counts: (font_size, count) for all fonts occuring in document
    :type font_counts: list
    :param styles: all styles found in the document
    :type styles: dict
    :rtype: dict
    :return: all element tags based on font-sizes
    """
    p_style = styles[font_counts[0][0]]  # get style for most used font by count (paragraph)
    p_size = p_style['size']  # get the paragraph's size

    # sorting the font sizes high to low, so that we can append the right integer to each tag
    font_sizes = []
    for (font_size, count) in font_counts:
        font_sizes.append(float(font_size))
    font_sizes.sort(reverse=True)

    # aggregating the tags for each font size
    idx = 0
    size_tag = {}
    for size in font_sizes:
        idx += 1
        if size == p_size:
            idx = 0
            size_tag[size] = ''
        if size > p_size:
            size_tag[size] = get_needed_hash(idx)
        elif size < p_size:
            size_tag[size] = ''

    return p_size, size_tag

def get_needed_hash(req_no_of_hash):
    no_hash = 0
    hash_string = ''
    while no_hash < req_no_of_hash:
        hash_string = hash_string + '#'
        no_hash = no_hash + 1
    return hash_string

def headers_para(doc, size_tag, para_size, length):
    """Scrapes headers & paragraphs from PDF and return texts with element tags.
    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param size_tag: textual element tags for each size
    :type size_tag: dict
    :rtype: list
    :return: texts with pre-prended element tags
    """
    header_para = []  # list with headers and paragraphs
    first = True  # boolean operator for first header
    previous_s = {}  # previous span
    header_contents = {}
    header = '-1 start_of_file'
    header_contents[header] = ''
    previous_header_hash = ''
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # this block contains text

                # REMEMBER: multiple fonts and sizes are possible IN one block

                block_string = ""  # text found in block
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if s['text'].strip():  # removing whitespaces:
                            if "Notation" in s['text'] or "What is a Tick?" in s['text']:
                                print('check ' + s['text'] + ' ' + str(s['font']) + ' ' + str(s['flags']) + ' ' + str(s['size']) + ' ' + str(s['color']))
                            if first:
                                previous_s = s
                                first = False
                                block_string = size_tag[s['size']] + s['text']
                            else:
                                if s['size'] == previous_s['size'] and s['flags'] == previous_s['flags']:
                                    if block_string and all((c == "|") for c in block_string):
                                        # block_string only contains pipes
                                        block_string = size_tag[s['size']] + s['text']
                                    if block_string == "":
                                        # new block has started, so append size tag
                                        block_string = size_tag[s['size']] + s['text']
                                    else:  # in the same block, so concatenate strings
                                        block_string += " " + s['text']

                                else:
                                    if s['size'] > para_size and block_string.strip() != '' and not(block_string.strip().isdigit()):
                                        header = size_tag[s['size']] + block_string
                                        header_contents[header] = ''
                                        previous_header_hash = size_tag[s['size']]
                                    # if same size as paragraph, check if there is bolding
                                    # if it is bold then we need to check that it is not just a digit or an empty string
                                    # check if the string starts with a caps
                                    # if it occupies full line, then again ignore as header
                                    elif check_bold_headers(length, para_size, s):
                                        header = previous_header_hash + '#' + s['text']
                                        header_contents[header] = ''
                                    else:
                                        header_contents[header] = header_contents[header] + ' ' + block_string
                                    block_string = size_tag[s['size']] + s['text']

                                previous_s = s

                if block_string != '' and not re.match(r'^[_\W]+$', block_string) and not(block_string.strip().isdigit()):
                    if s['size'] > para_size:
                        header = block_string
                        header_contents[header] = ''
                        previous_header_hash = size_tag[s['size']]
                    elif check_bold_headers(length, para_size, s):
                        header = previous_header_hash + '#' + block_string
                        header_contents[header] = ''
                    else:
                        header_contents[header] = header_contents[header] + block_string
    return header_contents


def check_bold_headers(length, para_size, s):
    try:
        return_value = s['size'] == para_size and s['flags'] > BOLD_FLAGS and s['text'].strip() != '' and not (s['text'].strip().isdigit()) \
                   and (s['text'][0].isupper() or (s['text'][0].isdigit() and s['text'].split(' ', 1)[1][0].isupper())) and (s['bbox'][2] - s['bbox'][0]) < length
    except IndexError:
        return False
    return return_value



def create_final_output(header_contents):
    output = ''

    for key in header_contents:
        if key.strip()!= '' and 'start_of_file' not in key:
            output = output + key + ' ' + '\n'
        if header_contents[key].strip() != '':
            output = output + header_contents[key].strip() + '\n'
    return output

def main():

    document = 'PATH_TO_DOCUMENT'
    doc = fitz.open(document)

    para_length = get_para_length(doc)

    font_counts, styles = fonts(doc, granularity=False)

    para_size, size_tag = font_tags(font_counts, styles)

    elements = headers_para(doc, size_tag, para_size, para_length)
    final_output = create_final_output(elements)
    print(final_output)


if __name__ == '__main__':
    main()
