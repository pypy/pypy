import autopath
from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.parsing import ParseError
from pypy.rlib.parsing.tree import RPythonVisitor

DEBUG = False

grammar = r'''
STRING: "\"([^\\\"]|\\\"|\\\\)*\"";
IDENTIFIER: "[\+\-\*\^\?a-zA-Z0-9!<=>_~/$%&:]+";
IGNORE: " |\n|\t|;[^\n]*";
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
    tree = t.visit(ToAST())[0]
    if DEBUG:
        ToAST().transform(t).view()
    return tree

class ASTBuilder(RPythonVisitor):

    def visit_STRING(self, node):
        print node.symbol + ":" + node.additional_info

    def visit_IDENTIFIER(self, node):
        print node.symbol + ":" + node.additional_info

    def visit_sexpr(self, node):
        print node.symbol + ":("
        nodes = [self.dispatch(child) for child in node.children]
        print ")"

