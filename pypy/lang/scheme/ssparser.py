import autopath
from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.parsing import ParseError

DEBUG = False

grammar = r'''
STRING: "\"([^\\\"]|\\\"|\\\\)*\"";
IDENTIFIER: "[\+\-\*\^\?a-zA-Z0-9!<=>_~/$%&:]+";
IGNORE: " |\n|\t|;[^\n]*";
progn: sexpr sexpr+
sexpr: ["("] sexpr* [")"] | <IDENTIFIER> | <STRING>;
'''
try:
	regexs, rules, ToAST = parse_ebnf(grammar)
except ParseError, e:
	#print e.nice_error_message()
	raise

parsef = make_parse_function(regexs, rules, eof=True)

def parse(code):
	t = parsef(code) 
	tree = t.visit(ToAST())
	if DEBUG:
		ToAST().transform(t).view()
	return tree

