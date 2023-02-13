from operator import itemgetter
import fitz

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
            size_tag[size] = '<p>'
        if size > p_size:
            size_tag[size] = '<h{0}>'.format(idx)
        elif size < p_size:
            size_tag[size] = '<s{0}>'.format(idx)

    return size_tag


def headers_para(doc, size_tag):
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

    for page in doc:
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
                                block_string = size_tag[s['size']] + s['text']
                            else:
                                if s['size'] == previous_s['size']:

                                    if block_string and all((c == "|") for c in block_string):
                                        # block_string only contains pipes
                                        block_string = size_tag[s['size']] + s['text']
                                    if block_string == "":
                                        # new block has started, so append size tag
                                        block_string = size_tag[s['size']] + s['text']
                                    else:  # in the same block, so concatenate strings
                                        block_string += " " + s['text']

                                else:
                                    header_para.append(block_string)
                                    block_string = size_tag[s['size']] + s['text']

                                previous_s = s

                    # new block started, indicating with a pipe
                    block_string += "|"

                header_para.append(block_string)

    return header_para


def main():

    document = '/Users/abhisheksomani/Downloads/Dfyn_V2_Whitepaper.pdf'
    doc = fitz.open(document)

    font_counts, styles = fonts(doc, granularity=True)

    size_tag = font_tags(font_counts, styles)

    elements = headers_para(doc, size_tag)

    print(elements)


if __name__ == '__main__':
    main()


# {'number': 13, 'type': 0, 'bbox': (93.54299926757812, 577.9452514648438, 233.81109619140625, 588.2067260742188), 'lines': [{'spans': [
# {'size': 9.962599754333496, 'flags': 20, 'font': 'CMSSBX10', 'color': 0, 'ascender': 0.7799999713897705, 'descender': -0.25, 'text': 'DApp', 'origin': (93.54299926757812, 585.716064453125), 'bbox': (93.54299926757812, 577.9452514648438, 119.62509155273438, 588.2067260742188)},
# {'size': 9.962599754333496, 'flags': 4, 'font': 'CMSS10', 'color': 0, 'ascender': 0.7590000033378601, 'descender': -0.25, 'text': ' Decentralized Application.', 'origin': (119.62509155273438, 585.716064453125), 'bbox': (119.62509155273438, 578.1544799804688, 233.81109619140625, 588.2067260742188)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (93.54299926757812, 577.9452514648438, 233.81109619140625, 588.2067260742188)}]}
# {'number': 0, 'type': 0, 'bbox': (93.54299926757812, 95.73521423339844, 207.66456604003906, 105.99668884277344), 'lines': [{'spans': [
# {'size': 9.962599754333496, 'flags': 20, 'font': 'CMSSBX10', 'color': 0, 'ascender': 0.7799999713897705, 'descender': -0.25, 'text': '1.2.1', 'origin': (93.54299926757812, 103.50604248046875), 'bbox': (93.54299926757812, 95.73521423339844, 116.07839965820312, 105.99668884277344)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (93.54299926757812, 95.73521423339844, 116.07839965820312, 105.99668884277344)}, {'spans': [{'size': 9.962599754333496, 'flags': 20, 'font': 'CMSSBX10', 'color': 0, 'ascender': 0.7799999713897705, 'descender': -0.25, 'text': 'Dfyn V1 Features', 'origin': (127.03726196289062, 103.50604248046875), 'bbox': (127.03726196289062, 95.73521423339844, 207.66456604003906, 105.99668884277344)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (127.03726196289062, 95.73521423339844, 207.66456604003906, 105.99668884277344)}]}



# {'number': 13, 'type': 0, 'bbox': (93.54299926757812, 577.9452514648438, 233.81109619140625, 588.2067260742188), 'lines': [{'spans': [
# {'size': 9.962599754333496, 'flags': 20, 'font': 'CMSSBX10', 'color': 0, 'ascender': 0.7799999713897705, 'descender': -0.25, 'text': 'DApp', 'origin': (93.54299926757812, 585.716064453125), 'bbox': (93.54299926757812, 577.9452514648438, 119.62509155273438, 588.2067260742188)},
# {'size': 9.962599754333496, 'flags': 4, 'font': 'CMSS10', 'color': 0, 'ascender': 0.7590000033378601, 'descender': -0.25, 'text': ' Decentralized Application.', 'origin': (119.62509155273438, 585.716064453125), 'bbox': (119.62509155273438, 578.1544799804688, 233.81109619140625, 588.2067260742188)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (93.54299926757812, 577.9452514648438, 233.81109619140625, 588.2067260742188)}]}
# {'number': 0, 'type': 0, 'bbox': (93.54299926757812, 95.73521423339844, 207.66456604003906, 105.99668884277344), 'lines': [{'spans': [
# {'size': 9.962599754333496, 'flags': 20, 'font': 'CMSSBX10', 'color': 0, 'ascender': 0.7799999713897705, 'descender': -0.25, 'text': '1.2.1', 'origin': (93.54299926757812, 103.50604248046875), 'bbox': (93.54299926757812, 95.73521423339844, 116.07839965820312, 105.99668884277344)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (93.54299926757812, 95.73521423339844, 116.07839965820312, 105.99668884277344)}, {'spans': [{'size': 9.962599754333496, 'flags': 20, 'font': 'CMSSBX10', 'color': 0, 'ascender': 0.7799999713897705, 'descender': -0.25, 'text': 'Dfyn V1 Features', 'origin': (127.03726196289062, 103.50604248046875), 'bbox': (127.03726196289062, 95.73521423339844, 207.66456604003906, 105.99668884277344)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (127.03726196289062, 95.73521423339844, 207.66456604003906, 105.99668884277344)}]}
# {'spans': [{'size': 9.962599754333496, 'flags': 4, 'font': 'CMSS10', 'color': 0, 'ascender': 0.7590000033378601, 'descender': -0.25, 'text': 'With Dfyn V2, we have taken this foundational innovation as our inspiration and built a so-', 'origin': (108.48699951171875, 521.1009521484375), 'bbox': (108.48699951171875, 513.5393676757812, 501.820556640625, 523.5916137695312)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (108.48699951171875, 513.5393676757812, 501.820556640625, 523.5916137695312)}
# {'spans': [{'size': 9.962599754333496, 'flags': 4, 'font': 'CMSS10', 'color': 0, 'ascender': 0.7590000033378601, 'descender': -0.25, 'text': 'phisticated solution for all classes of crypto traders in the space. Before we dive deep into the', 'origin': (93.54299926757812, 533.0569458007812), 'bbox': (93.54299926757812, 525.495361328125, 501.7406921386719, 535.547607421875)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (93.54299926757812, 525.495361328125, 501.7406921386719, 535.547607421875)}
# {'spans': [{'size': 11.9552001953125, 'flags': 20, 'font': 'CMSSBX10', 'color': 0, 'ascender': 0.7799999713897705, 'descender': -0.25, 'text': '1.1', 'origin': (93.54299926757812, 132.10198974609375), 'bbox': (93.54299926757812, 122.77693176269531, 110.35202026367188, 135.09078979492188)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (93.54299926757812, 122.77693176269531, 110.35202026367188, 135.09078979492188)}
# {'spans': [{'size': 11.9552001953125, 'flags': 20, 'font': 'CMSSBX10', 'color': 0, 'ascender': 0.7799999713897705, 'descender': -0.25, 'text': 'Background', 'origin': (123.50273895263672, 132.10198974609375), 'bbox': (123.50273895263672, 122.77693176269531, 188.45533752441406, 135.09078979492188)}], 'wmode': 0, 'dir': (1.0, 0.0), 'bbox': (123.50273895263672, 122.77693176269531, 188.45533752441406, 135.09078979492188)}

# 'bbox': (123.50273895263672, 122.77693176269531, 188.45533752441406, 135.09078979492188) -> x0, y0, x1, y1 -> check if full line, then treat as normal text but if partial line then treat as heading?
# does't work where the partial line ends in next line
# not ending with a !, ., ? ---- not so elegant
# first character is caps or caps followed by digit

# string = '1 Ckah'
# if string[0].isupper() or (string[0].isdigit() and string.split(' ', 1)[1][0].isupper()):
#     print('hello')


# s['size'] == para_size and s['flags'] > BOLD_FLAGS and block_string.strip() != '' and not(block_string.strip().isdigit()) \
#     and (block_string[0].isupper() or (block_string[0].isdigit() and block_string.split(' ', 1)[1][0].isupper())) \
#     and (s['bbox'][2] - s['bbox'][0]) < length: