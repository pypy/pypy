from pypy.rlib.parsing.ebnfparse import parse_ebnf, make_parse_function
from pypy.rlib.parsing.parsing import ParseError, Rule
from pypy.rlib.parsing.tree import RPythonVisitor, Symbol
from pypy.lang.js.jsobj import W_Number
from pypy.lang.js import operations
import sys

##try:
##    t = open("jsgrammar.txt").read()
##    regexs, rules, ToAST = parse_ebnf(t)
##except ParseError,e:
##    print e.nice_error_message(filename="jsgrammar.txt",source=t)
##    sys.exit(1)
##
##def setstartrule(rules, start):
##    "takes the rule start and put it on the beginning of the rules"
##    oldpos = 0
##    newrules = [Rule("hacked_first_symbol", [[start, "EOF"]])] + rules
##    return newrules
##
##if len(sys.argv) == 1:
##    parse = make_parse_function(regexs, rules, eof=True)
##else:
##    parse = make_parse_function(regexs, setstartrule(rules,sys.argv[1]), eof=True)
##
##print rules[2].nonterminal
##source = raw_input()
##while source != "":
##    t = parse(source).children[0].visit(ToAST())[0]
##    print t
##    t.view()
##    source = raw_input()

class EvalTreeBuilder(RPythonVisitor):
    BINOP_TO_CLS = {
        '+': operations.Plus,
        '-': operations.Minus,
        '*': operations.Mult,
        '/': operations.Div,
        '%': operations.Mod,
    }
    UNOP_TO_CLS = {
        '+': operations.UPlus,
        '-': operations.UMinus,
        '++': operations.Increment,
        '--': operations.Decrement,
    }
    def get_instance(self, symbol, cls):
        assert isinstance(symbol, Symbol)
        source_pos = symbol.token.source_pos
        # XXX some of the source positions are not perfect
        return cls(None, "no clue what self.type is used for",
                   symbol.additional_info, 
                   source_pos.lineno,
                   source_pos.columnno,
                   source_pos.columnno + len(symbol.additional_info))

    def visit_DECIMALLITERAL(self, node):
        result = self.get_instance(node, operations.Number)
        result.num = float(node.additional_info)
        return result

    def string(self,node):
        print node.additional_info
        result = self.get_instance(node, operations.String)
        result.strval = node.additional_info[1:-1] #XXX should do unquoting
        return result
    
    visit_DOUBLESTRING = string
    visit_SINGLESTRING = string

    def binaryop(self, node):
        left = self.dispatch(node.children[0])
        for i in range((len(node.children) - 1) // 2):
            op = node.children[i * 2 + 1]
            result = self.get_instance(
                    op, self.BINOP_TO_CLS[op.additional_info])
            right = self.dispatch(node.children[i * 2 + 2])
            result.left = left
            result.right = right
            left = result
        return left

    visit_additiveexpression = binaryop
    visit_multiplicativeexpression = binaryop

    def visit_unaryexpression(self, node):
        op = node.children[0]
        result = self.get_instance(
                op, self.UNOP_TO_CLS[op.additional_info])
        child = self.dispatch(node.children[1])
        result.expr = child
        result.postfix = False
        return result

