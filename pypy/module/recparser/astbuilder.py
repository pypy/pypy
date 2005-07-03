

from grammar import BaseGrammarBuilder
from compiler.ast import nodes, TokenNode
from compiler.astfactory import factory_functions, group_factory, syntaxnode_factory

class AstBuilder(BaseGrammarBuilder):
    """A builder that directly produce the AST"""

    def __init__( self, rules=None, debug=0 ):
        BaseGrammarBuilder.__init__(self, rules, debug )

    def top(self, n=1):
        toplist = []
        for node in self.stack[-n:]:
            toplist += node.expand()
        return toplist

    def alternative( self, rule, source ):
        # Do nothing, keep rule on top of the stack
        if rule.is_root():
            ast_factory = factory_functions.get( rule.name, syntaxnode_factory )
            elems = self.top()
            node = ast_factory( rule.name, source, elems )
            self.stack[-1] = node
            if self.debug:
                self.stack[-1].dumpstr()
        return True

    def sequence(self, rule, source, elts_number):
        """ """
        items = self.top( elts_number )
        if rule.is_root():
            ast_factory = factory_functions.get( rule.name, syntaxnode_factory )
        else:
            ast_factory = group_factory

        node = ast_factory( rule.name, source, items )
        # replace N elements with 1 element regrouping them
        if elts_number >= 1:
            self.stack[-elts_number:] = node
        else:
            self.stack.append(node)
        return True

    def token(self, name, value, source):
        self.stack.append(TokenNode(name, source, value))
        return True
