"""
A CPython inspired RPython parser.
"""


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
        self.dfas = {}
        self.labels = [0]
        self.token_ids = {}

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


class Node(object):

    __slots__ = "type value children lineno column".split()

    def __init__(self, type, value, children, lineno, column):
        self.type = type
        self.value = value
        self.children = children
        self.lineno = lineno
        self.column = column

    def __eq__(self, other):
        # For tests.
        return (self.type == other.type and
                self.value == other.value and
                self.children == other.children)

    def __repr__(self):
        if self.value is None:
            return "Node(type=%s, children=%r)" % (self.type, self.children)
        else:
            return "Node(type=%s, value=%r)" % (self.type, self.value)


class ParseError(Exception):

    def __init__(self, msg, token_type, value, lineno, column, line,
                 expected=-1):
        self.msg = msg
        self.token_type = token_type
        self.value = value
        self.lineno = lineno
        self.column = column
        self.line = line
        self.expected = expected

    def __str__(self):
        return "ParserError(%s, %r)" % (self.token_type, self.value)


class Parser(object):

    def __init__(self, grammar):
        self.grammar = grammar
        self.root = None
        self.stack = None

    def prepare(self, start=-1):
        """Setup the parser for parsing.

        Takes the starting symbol as an argument.
        """
        if start == -1:
            start = self.grammar.start
        self.root = None
        current_node = Node(start, None, [], 0, 0)
        self.stack = []
        self.stack.append((self.grammar.dfas[start], 0, current_node))

    def add_token(self, token_type, value, lineno, column, line):
        label_index = self.classify(token_type, value, lineno, column, line)
        sym_id = 0 # for the annotator
        while True:
            dfa, state_index, node = self.stack[-1]
            states, first = dfa
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
                        if not self.stack:
                            # Parsing is done.
                            return True
                        dfa, state_index, node = self.stack[-1]
                        state = dfa[0][state_index]
                    return False
                elif sym_id >= 256:
                    sub_node_dfa = self.grammar.dfas[sym_id]
                    # Check if this token can start a child node.
                    if label_index in sub_node_dfa[1]:
                        self.push(sub_node_dfa, next_state, sym_id, lineno,
                                  column)
                        break
            else:
                # We failed to find any arcs to another state, so unless this
                # state is accepting, it's invalid input.
                if is_accepting:
                    self.pop()
                    if not self.stack:
                        raise ParseError("too much input", token_type, value,
                                         lineno, column, line)
                else:
                    # If only one possible input would satisfy, attach it to the
                    # error.
                    if len(arcs) == 1:
                        expected = sym_id
                    else:
                        expected = -1
                    raise ParseError("bad input", token_type, value, lineno,
                                     column, line, expected)

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
        dfa, state, node = self.stack[-1]
        new_node = Node(token_type, value, None, lineno, column)
        node.children.append(new_node)
        self.stack[-1] = (dfa, next_state, node)

    def push(self, next_dfa, next_state, node_type, lineno, column):
        """Push a terminal and adjust the current state."""
        dfa, state, node = self.stack[-1]
        new_node = Node(node_type, None, [], lineno, column)
        self.stack[-1] = (dfa, next_state, node)
        self.stack.append((next_dfa, 0, new_node))

    def pop(self):
        """Pop an entry off the stack and make its node a child of the last."""
        dfa, state, node = self.stack.pop()
        if self.stack:
            self.stack[-1][2].children.append(node)
        else:
            self.root = node
