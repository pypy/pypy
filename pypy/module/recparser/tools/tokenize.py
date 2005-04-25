
import sys
from python.lexer import PythonSource


def parse_file(filename):
    f = file(filename).read()
    src = PythonSource(f)
    token = src.next()
    while token!=("ENDMARKER",None) and token!=(None,None):
        print token
        token = src.next()

if __name__ == '__main__':
    parse_file(sys.argv[1])
