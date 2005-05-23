
from grammar import BaseGrammarBuilder
from syntaxtree import TOKEN_MAP, SYMBOLS, NT_OFFSET


def _expand_nodes( nodes ):
    expanded = []
    for n in nodes:
        if n[0]==-2:
            expanded.extend( expand_nodes(n[1:]) )
        else:
            expanded.append(n)
    return tuple(expanded)

def expand_nodes( nodes ):
    r = _expand_nodes( nodes )
    for n in nodes:
        assert type(n[0])==int
    return r
        
class TupleBuilder(BaseGrammarBuilder):
    """A builder that directly produce the AST"""

    def __init__( self, rules=None, debug=0, lineno=False ):
        BaseGrammarBuilder.__init__(self, rules, debug )
        self.lineno = True

    def alternative( self, rule, source ):
        # Do nothing, keep rule on top of the stack
        if rule.is_root():
            node = [ SYMBOLS.get( rule.name, (0,rule.name) ) ]
            node +=  expand_nodes( [self.stack[-1]] )
            self.stack[-1] = tuple(node)
        return True

    def sequence(self, rule, source, elts_number):
        """ """
        if rule.is_root():
            node  = [ SYMBOLS.get( rule.name, (0,rule.name) ) ]
        else:
            node = [ -2 ]
        if elts_number>0:
            node += expand_nodes( self.stack[-elts_number:] )
            self.stack[-elts_number:] = [tuple(node)]
        else:
            self.stack.append( tuple(node) )
        return True

    def token(self, name, value, source):
        num = TOKEN_MAP.get( name, -1)
        lineno = source.current_line()
        if value is None:
            if name not in ("NEWLINE", "INDENT", "DEDENT", "ENDMARKER"):
                value = name
            else:
                value = ''
        if self.lineno:
            self.stack.append( (num, value, lineno) )
        else:
            self.stack.append( (num, value) )
        return True
