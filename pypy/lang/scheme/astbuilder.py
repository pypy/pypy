import autopath
from pypy.rlib.parsing.tree import RPythonVisitor

class ASTBuilder(RPythonVisitor):

    def visit_STRING(self, node):
        print node.symbol + ":" + node.additional_info

    def visit_IDENTIFIER(self, node):
        print node.symbol + ":" + node.additional_info

    def visit_sexpr(self, node):
        print node.symbol + ":("
        nodes = [self.dispatch(child) for child in node.children]
        print ")"

