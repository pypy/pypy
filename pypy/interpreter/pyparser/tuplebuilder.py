
from grammar import BaseGrammarBuilder
from pytoken import tok_name, tok_rpunct, NEWLINE, INDENT, DEDENT, ENDMARKER

class StackElement:
    """wraps TupleBuilder's tuples"""

class Terminal(StackElement):
    def __init__(self, num, value, lineno=-1):
        self.nodes = [(num, value, lineno)]
        self.num = num

    def as_tuple(self, lineno=False):
        if lineno:
            return self.nodes[0]
        else:
            return self.nodes[0][:-1]

class NonTerminal(StackElement):
    def __init__(self, num, nodes):
        """rulename should always be None with regular Python grammar"""
        self.nodes = nodes
        self.num = num

    def as_tuple(self, lineno=False):
        l = [self.num] + [node.as_tuple(lineno) for node in self.nodes]
        return tuple(l)
    
        
def expand_nodes(stack_elements):
    """generate a nested tuples from a list of stack elements"""
    expanded = []
    for element in stack_elements:
        if isinstance(element, NonTerminal) and element.num<0:
            expanded.extend(element.nodes)
        else:
            expanded.append(element)
    return expanded

class TupleBuilder(BaseGrammarBuilder):
    """A builder that directly produce the AST"""

    def __init__(self, rules=None, debug=0, lineno=True):
        BaseGrammarBuilder.__init__(self, rules, debug)
        # This attribute is here for convenience
        self.source_encoding = None
        self.lineno = lineno
        self.tuplestack = []
        
    def alternative(self, rule, source):
        # Do nothing, keep rule on top of the stack
        if rule.is_root():
            nodes = expand_nodes( [self.stack[-1]] )
            self.stack[-1] = NonTerminal( rule.codename, nodes )
        return True
            
    def sequence(self, rule, source, elts_number):
        """ """
        num = rule.codename
        node = [rule.codename]
        if elts_number > 0:
            sequence_elements = self.stack[-elts_number:]
            nodes = expand_nodes( sequence_elements )
            self.stack[-elts_number:] = [NonTerminal(num, nodes)]
        else:
            self.stack.append( NonTerminal(num, []) )
        return True

    def token(self, codename, value, source):
        lineno = source.current_lineno()
        if value is None:
            if codename not in ( NEWLINE, INDENT, DEDENT, ENDMARKER ):
                value = tok_rpunct.get(codename, "unknown op")
            else:
                value = ''
        self.stack.append( Terminal(codename, value, lineno) )
        return True
