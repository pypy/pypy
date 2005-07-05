
from grammar import BaseGrammarBuilder
from syntaxtree import TOKEN_MAP # , NT_OFFSET
from pythonparse import SYMBOLS

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
    def __init__(self, num, nodes, rulename=None):
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
        if isinstance(element, NonTerminal) and element.num == -2:
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
        self._unknown = -10
        
    def _add_rule(self, rulename):
        SYMBOLS[rulename] = self._unknown
        self._unknown -= 1

    def alternative(self, rule, source):
        # Do nothing, keep rule on top of the stack
        if rule.is_root():
            nodes = expand_nodes( [self.stack[-1]] )
            if rule.name in SYMBOLS:
                self.stack[-1] = NonTerminal(SYMBOLS[rule.name], nodes)
            else:
                # Using regular CPython's Grammar should not lead here
                # XXX find how self._unknown is meant to be used
                self.stack[-1] = NonTerminal(self._unknown, nodes, rule.name)
                self._add_rule(rule.name)
        return True
            
    def sequence(self, rule, source, elts_number):
        """ """
        if rule.is_root():
            if rule.name in SYMBOLS:
                num = SYMBOLS[rule.name]
                node = [num]
            else:
                num = self._unknown
                node = [num]
                self._add_rule(rule.name)
        else:
            num = -2
            node = [num]
        if elts_number > 0:
            sequence_elements = self.stack[-elts_number:]
            nodes = expand_nodes( sequence_elements )
            self.stack[-elts_number:] = [NonTerminal(num, nodes)]
        else:
            self.stack.append( NonTerminal(num, []) )
        return True

    def token(self, name, value, source):
        num = TOKEN_MAP.get(name, -1)
        lineno = source.current_lineno()
        if value is None:
            if name not in ("NEWLINE", "INDENT", "DEDENT", "ENDMARKER"):
                value = name
            else:
                value = ''
        self.stack.append( Terminal(num, value, lineno) )
        return True
