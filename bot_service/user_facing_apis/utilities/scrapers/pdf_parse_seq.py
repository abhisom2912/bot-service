from operator import itemgetter
import fitz
import re
import numpy as np

# script to parse data from an entire PDF and converting it into MD format

def get_max_header_levels(header_contents):
    max_level = 0
    for key in header_contents:
        key_level = key.count('.') + 1
        if key_level > max_level:
            max_level = key_level
    return max_level

def get_most_used_font_styles(doc):
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
    total_spans = 0
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        identifier = "{0}_{1}_{2}_{3}".format(s['size'], s['flags'], s['font'], s['color'])
                        styles[identifier] = {'size': s['size'], 'flags': s['flags'], 'font': s['font'],
                                              'color': s['color']}

                        font_counts[identifier] = font_counts.get(identifier, 0) + 1  # count the fonts usage
                        total_spans = total_spans + 1

    font_counts = sorted(font_counts.items(), key=itemgetter(1), reverse=True)

    counts_array = []
    for key, value in font_counts:
        counts_array.append(value)

    para_style_keys = []
    para_styles_count = max(np.percentile(counts_array, 95), np.average(counts_array))
    for key, value in font_counts:
        if value >= para_styles_count:
            para_style_keys.append(key)

    if len(font_counts) < 1:
        raise ValueError("Zero discriminating fonts found!")

    para_styles = []
    for key in styles:
        if para_style_keys.count(key) != 0:
            para_styles.append(styles[key])

    return para_styles # get styles for most used font by count (paragraph)

def headers_para(doc, table_of_contents_pages):
    """Scrapes headers & paragraphs from PDF and return texts with element tags.
    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param size_tag: textual element tags for each size
    :type size_tag: dict
    :rtype: list
    :return: texts with pre-prended element tags
    """
    para_font_styles = get_most_used_font_styles(doc)
    first = True  # boolean operator for first header
    previous_s = {}  # previous span
    header_contents = {}
    header = '-1 start_of_file'
    header_contents[header] = ''
    for page in doc:
        if page.number + 1 in table_of_contents_pages:
            continue
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # this block contains text

                # REMEMBER: multiple fonts and sizes are possible IN one block

                block_string = ""  # text found in block
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if s['text'].strip():  # removing whitespaces:
                            if first:
                                previous_s = s
                                first = False
                                block_string = s['text']
                            else:
                                if s['size'] == previous_s['size'] and s['font'] == previous_s['font'] and s['flags'] == previous_s['flags']:
                                    if block_string == "":
                                        # new block has started
                                        block_string = s['text']
                                    else:  # in the same block, so concatenate strings
                                        block_string += " " + s['text']

                                else:
                                    # Check for a header, conditions -
                                    # First part contains numbers and "."
                                    # First letter is a digit
                                    # Should not be filled with only digits - to avoid footers
                                    # Ends with a digit, as sections always end with a digit
                                    # Style is not same as the paragraph style
                                    if re.match('^[0-9\.]*$', block_string.split(" ")[0]) and block_string[:1].isdigit() \
                                            and not(block_string.strip().isdigit()) and bool(re.search(r'\d+$', block_string.split(" ")[0])):
                                            # and compare_fonts(para_font_styles, s):
                                        previous_header_num = header.split(" ")[0]
                                        if validate_new_num(block_string.split(" ")[0], previous_header_num):
                                            header = block_string
                                            header_contents[header] = ''
                                        else:
                                            header_contents[header] = header_contents[header] + block_string
                                    else:
                                        header_contents[header] = header_contents[header] + ' ' + block_string
                                    block_string = s['text']

                                previous_s = s
                # is not empty and is not only special characters
                if block_string != '' and not re.match(r'^[_\W]+$', block_string):
                    if re.match('^[0-9\.]*$', block_string.split(" ")[0]) and block_string[:1].isdigit() \
                            and not(block_string.strip().isdigit()) and bool(re.search(r'\d+$', block_string.split(" ")[0])):
                        previous_header_num = header.split(" ")[0]
                        if validate_new_num(block_string.split(" ")[0], previous_header_num):
                            header = block_string
                            header_contents[header] = ''
                        else:
                            header_contents[header] = header_contents[header] + block_string
                    else:
                        header_contents[header] = header_contents[header] + block_string
    return header_contents

def compare_fonts(font_styles, s):
    for font_style in font_styles:
        if s['size'] == font_style['size'] and s['flags'] == font_style['flags'] and s['font'] == font_style['font'] and s['color'] == font_style['color']:
            return False
    return True

def validate_new_num(new_header_num, previous_header_num):
    if new_header_num == previous_header_num:
        return False
    count_places = min(new_header_num.count('.'), previous_header_num.count('.'))
    i = count_places
    all_digit_same = True
    while i >= 0:
        if new_header_num.split('.')[i] < previous_header_num.split('.')[i]:
            return False
        if new_header_num.split('.')[i] ==  previous_header_num.split('.')[i]:
            all_digit_same = all_digit_same & True
        else:
            all_digit_same = all_digit_same & False
        i = i - 1
    if all_digit_same:
        if new_header_num.count('.') < previous_header_num.count('.'):
            return False
    return True

def get_needed_hash(header, max_level):
    req_no_of_hash = header.count(".") + 1
    if str(header).endswith('.'):
        req_no_of_hash = max_level + 1
    no_hash = 0
    hash_string = ''
    while no_hash < req_no_of_hash:
        hash_string = hash_string + '#'
        no_hash = no_hash + 1
    return hash_string

def create_final_output(header_contents):
    output = ''
    max_level = get_max_header_levels(header_contents)
    for key in header_contents:
        header = key.split(' ', 1)[1]
        if header.strip()!= '' and header != 'start_of_file':
            output = output + get_needed_hash(key.split(' ')[0], max_level) + ' ' + header.strip() + '\n'
        if header_contents[key].strip() != '':
            output = output + header_contents[key].strip() + '\n'
    return output

def convert_to_md_format(document, table_of_contents_pages):
    doc = fitz.open(document)

    header_contents = headers_para(doc, table_of_contents_pages)
    return create_final_output(header_contents)

def main():
    document = 'PATH_TO_DOCUMENT'
    table_of_contents_pages = [2, 3] # need to specify the table of contents_pages so that they can be ignored
    print(convert_to_md_format(document, table_of_contents_pages))


if __name__ == '__main__':
    main()