from fuzzywuzzy import fuzz

def main():
    Str1 = "Back"
    Str2 = "Book"
    Ratio = fuzz.ratio(Str1.lower(),Str2.lower())
    print(Ratio)


if __name__ == '__main__':
    main()