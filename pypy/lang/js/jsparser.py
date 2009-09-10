from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.parsing import ParseError, Rule
import py

GFILE = py.magic.autopath().dirpath().join("jsgrammar.txt")

try:
    t = GFILE.read(mode='U')
    regexs, rules, ToAST = parse_ebnf(t)
except ParseError,e:
    print e.nice_error_message(filename=str(GFILE),source=t)
    raise

parsef = make_parse_function(regexs, rules, eof=True)

def parse(code):
    t = parsef(code)
    return ToAST().transform(t)
