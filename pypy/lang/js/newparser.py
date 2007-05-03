from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.parsing import ParseError, Rule
import sys

try:
    t = open("jsgrammar.txt").read()
    regexs, rules, ToAST = parse_ebnf(t)
except ParseError,e:
    print e.nice_error_message(filename="jsgrammar.txt",source=t)
    sys.exit(1)

def setstartrule(rules, start):
    "takes the rule start and put it on the beginning of the rules"
    oldpos = 0
    newrules = [Rule("hacked_first_symbol", [[start, "EOF"]])] + rules
    return newrules

if len(sys.argv) == 1:
    parse = make_parse_function(regexs, rules, eof=True)
else:
    parse = make_parse_function(regexs, setstartrule(rules,sys.argv[1]), eof=True)

print rules[2].nonterminal
source = raw_input()
while source != "":
    t = parse(source).children[0].visit(ToAST())[0]
    print t
    t.view()
    source = raw_input()
