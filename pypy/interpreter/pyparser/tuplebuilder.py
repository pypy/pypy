
from grammar import AbstractBuilder, AbstractContext, Parser

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

    def as_w_tuple(self, space, lineno=False):
        num, value, lineno = self.nodes[0]
        if lineno:
            content = [space.wrap(num), space.wrap(value), space.wrap(lineno)]
        else:
            content = [space.wrap(num), space.wrap(value)]
        return space.newtuple(content)


class NonTerminal(StackElement):
    def __init__(self, num, nodes):
        """rulename should always be None with regular Python grammar"""
        self.nodes = nodes
        self.num = num

    def as_tuple(self, lineno=False):
        l = [self.num] + [node.as_tuple(lineno) for node in self.nodes]
        return tuple(l)

    def as_w_tuple(self, space, lineno=False):
        l = ([space.wrap(self.num)] +
             [node.as_w_tuple(space, lineno) for node in self.nodes])
        return space.newtuple(l)


def expand_nodes(stack_elements):
    """generate a nested tuples from a list of stack elements"""
    expanded = []
    for element in stack_elements:
        if isinstance(element, NonTerminal) and element.num<0:
            expanded.extend(element.nodes)
        else:
            expanded.append(element)
    return expanded

class TupleBuilderContext(AbstractContext):
    def __init__(self, stackpos ):
        self.stackpos = stackpos

class TupleBuilder(AbstractBuilder):
    """A builder that directly produce the AST"""

    def __init__(self, parser, debug=0, lineno=True):
        AbstractBuilder.__init__(self, parser, debug)
        # This attribute is here for convenience
        self.source_encoding = None
        self.lineno = lineno
        self.stack = []
        self.space_token = ( self.parser.tokens['NEWLINE'], self.parser.tokens['INDENT'],
                             self.parser.tokens['DEDENT'], self.parser.tokens['ENDMARKER'] )

    def context(self):
        """Returns the state of the builder to be restored later"""
        #print "Save Stack:", self.stack
        return TupleBuilderContext(len(self.stack))

    def restore(self, ctx):
        assert isinstance(ctx, TupleBuilderContext)
        del self.stack[ctx.stackpos:]
        #print "Restore Stack:", self.stack

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
            sequence_elements = [self.stack.pop() for i in range(elts_number)]
            sequence_elements.reverse()
            nodes = expand_nodes( sequence_elements )
        else:
            nodes = []
        self.stack.append( NonTerminal(num, nodes) )
        return True

    def token(self, codename, value, source):
        lineno = source._token_lnum
        if value is None:
            if codename not in self.space_token:
                value = self.parser.tok_rvalues.get(codename, "unknown op")
            else:
                value = ''
        self.stack.append( Terminal(codename, value, lineno) )
        return True
