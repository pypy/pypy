"""
A CPython inspired RPython parser.
"""
from rpython.rlib.objectmodel import not_rpython


class Grammar(object):
    """
    Base Grammar object.

    Pass this to ParserGenerator.build_grammar to fill it with useful values for
    the Parser.
    """

    def __init__(self):
        self.symbol_ids = {}
        self.symbol_names = {}
        self.symbol_to_label = {}
        self.keyword_ids = {}
        self.token_to_error_string = {}
        self.dfas = []
        self.labels = [0]
        self.token_ids = {}
        self.start = -1

    def shared_copy(self):
        new = self.__class__()
        new.symbol_ids = self.symbol_ids
        new.symbols_names = self.symbol_names
        new.keyword_ids = self.keyword_ids
        new.dfas = self.dfas
        new.labels = self.labels
        new.token_ids = self.token_ids
        return new

    def _freeze_(self):
        # Remove some attributes not used in parsing.
        try:
            del self.symbol_to_label
            del self.symbol_names
            del self.symbol_ids
        except AttributeError:
            pass
        return True

class DFA(object):
    def __init__(self, symbol_id, states, first):
        self.symbol_id = symbol_id
        self.states = states
        self.first = self._first_to_string(first)

    def could_match_token(self, label_index):
        pos = label_index >> 3
        bit = 1 << (label_index & 0b111)
        return bool(ord(self.first[label_index >> 3]) & bit)

    @staticmethod
    @not_rpython
    def _first_to_string(first):
        l = sorted(first.keys())
        b = bytearray(32)
        for label_index in l:
            pos = label_index >> 3
            bit = 1 << (label_index & 0b111)
            b[pos] |= bit
        return str(b)

class Node(object):

    __slots__ = ("type", )

    def __init__(self, type):
        self.type = type

    def __eq__(self, other):
        raise NotImplementedError("abstract base class")

    def __ne__(self, other):
        return not self == other

    def get_value(self):
        return None

    def get_child(self, i):
        raise NotImplementedError("abstract base class")

    def num_children(self):
        return 0

    def append_child(self, child):
        raise NotImplementedError("abstract base class")

    def get_lineno(self):
        raise NotImplementedError("abstract base class")

    def get_column(self):
        raise NotImplementedError("abstract base class")


class Terminal(Node):
    __slots__ = ("value", "lineno", "column")
    def __init__(self, type, value, lineno, column):
        Node.__init__(self, type)
        self.value = value
        self.lineno = lineno
        self.column = column

    def __repr__(self):
        return "Terminal(type=%s, value=%r)" % (self.type, self.value)

    def __eq__(self, other):
        # For tests.
        return (type(self) == type(other) and
                self.type == other.type and
                self.value == other.value)

    def get_value(self):
        return self.value

    def get_lineno(self):
        return self.lineno

    def get_column(self):
        return self.column


class AbstractNonterminal(Node):
    __slots__ = ()

    def get_lineno(self):
        return self.get_child(0).get_lineno()

    def get_column(self):
        return self.get_child(0).get_column()

    def __eq__(self, other):
        # For tests.
        # grumble, annoying
        if not isinstance(other, AbstractNonterminal):
            return False
        if self.type != other.type:
            return False
        if self.num_children() != other.num_children():
            return False
        for i in range(self.num_children()):
            if self.get_child(i) != other.get_child(i):
                return False
        return True


class Nonterminal(AbstractNonterminal):
    __slots__ = ("_children", )
    def __init__(self, type, children=None):
        Node.__init__(self, type)
        if children is None:
            children = []
        self._children = children

    def __repr__(self):
        return "Nonterminal(type=%s, children=%r)" % (self.type, self._children)

    def get_child(self, i):
        assert self._children is not None
        return self._children[i]

    def num_children(self):
        return len(self._children)

    def append_child(self, child):
        self._children.append(child)


class Nonterminal1(AbstractNonterminal):
    __slots__ = ("_child", )
    def __init__(self, type, child):
        Node.__init__(self, type)
        self._child = child

    def __repr__(self):
        return "Nonterminal(type=%s, children=[%r])" % (self.type, self._child)

    def get_child(self, i):
        assert i == 0 or i == -1
        return self._child

    def num_children(self):
        return 1

    def append_child(self, child):
        assert 0, "should be unreachable"



class ParseError(Exception):

    def __init__(self, msg, token_type, value, lineno, column, line,
                 expected=-1, expected_str=None):
        self.msg = msg
        self.token_type = token_type
        self.value = value
        self.lineno = lineno
        # this is a 0-based index
        self.column = column
        self.line = line
        self.expected = expected
        self.expected_str = expected_str

    def __str__(self):
        return "ParserError(%s, %r)" % (self.token_type, self.value)


class StackEntry(object):
    def __init__(self, next, dfa, state):
        self.next = next
        self.dfa = dfa
        self.state = state
        self.node = None

    def push(self, dfa, state):
        return StackEntry(self, dfa, state)

    def pop(self):
        return self.next

    def node_append_child(self, child):
        node = self.node
        if node is None:
            self.node = Nonterminal1(self.dfa.symbol_id, child)
        elif isinstance(node, Nonterminal1):
            newnode = self.node = Nonterminal(
                    self.dfa.symbol_id, [node._child, child])
        else:
            self.node.append_child(child)


class Parser(object):

    def __init__(self, grammar):
        self.grammar = grammar
        self.root = None

    def prepare(self, start=-1):
        """Setup the parser for parsing.

        Takes the starting symbol as an argument.
        """
        if start == -1:
            start = self.grammar.start
        self.root = None
        self.stack = StackEntry(None, self.grammar.dfas[start - 256], 0)

    def add_token(self, token_type, value, lineno, column, line):
        label_index = self.classify(token_type, value, lineno, column, line)
        sym_id = 0 # for the annotator
        while True:
            dfa = self.stack.dfa
            state_index = self.stack.state
            states = dfa.states
            arcs, is_accepting = states[state_index]
            for i, next_state in arcs:
                sym_id = self.grammar.labels[i]
                if label_index == i:
                    # We matched a non-terminal.
                    self.shift(next_state, token_type, value, lineno, column)
                    state = states[next_state]
                    # While the only possible action is to accept, pop nodes off
                    # the stack.
                    while state[1] and not state[0]:
                        self.pop()
                        if self.stack is None:
                            # Parsing is done.
                            return True
                        dfa = self.stack.dfa
                        state_index = self.stack.state
                        state = dfa.states[state_index]
                    return False
                elif sym_id >= 256:
                    sub_node_dfa = self.grammar.dfas[sym_id - 256]
                    # Check if this token can start a child node.
                    if sub_node_dfa.could_match_token(label_index):
                        self.push(sub_node_dfa, next_state, sym_id, lineno,
                                  column)
                        break
            else:
                # We failed to find any arcs to another state, so unless this
                # state is accepting, it's invalid input.
                if is_accepting:
                    self.pop()
                    if self.stack is None:
                        raise ParseError("too much input", token_type, value,
                                         lineno, column, line)
                else:
                    # If only one possible input would satisfy, attach it to the
                    # error.
                    if len(arcs) == 1:
                        expected = sym_id
                        expected_str = self.grammar.token_to_error_string.get(
                                arcs[0][0], None)
                    else:
                        expected = -1
                        expected_str = None
                    raise ParseError("bad input", token_type, value, lineno,
                                     column, line, expected, expected_str)

    def classify(self, token_type, value, lineno, column, line):
        """Find the label for a token."""
        if token_type == self.grammar.KEYWORD_TOKEN:
            label_index = self.grammar.keyword_ids.get(value, -1)
            if label_index != -1:
                return label_index
        label_index = self.grammar.token_ids.get(token_type, -1)
        if label_index == -1:
            raise ParseError("invalid token", token_type, value, lineno, column,
                             line)
        return label_index

    def shift(self, next_state, token_type, value, lineno, column):
        """Shift a non-terminal and prepare for the next state."""
        new_node = Terminal(token_type, value, lineno, column)
        self.stack.node_append_child(new_node)
        self.stack.state = next_state

    def push(self, next_dfa, next_state, node_type, lineno, column):
        """Push a terminal and adjust the current state."""
        self.stack.state = next_state
        self.stack = self.stack.push(next_dfa, 0)

    def pop(self):
        """Pop an entry off the stack and make its node a child of the last."""
        top = self.stack
        self.stack = top.pop()
        node = top.node
        assert node is not None
        if self.stack:
            self.stack.node_append_child(node)
        else:
            self.root = node
