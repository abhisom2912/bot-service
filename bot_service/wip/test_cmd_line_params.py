import sys

def main():
    arguments = {}
    n = len(sys.argv)

    print("\nArguments passed:", end = " ")
    for i in range(1, n):
        argument = sys.argv[i].split('=')
        arguments[argument[0]] = argument[1]
    print(arguments['axc'])
    print(arguments['axc'] == 'True')


if __name__ == '__main__':
    main()