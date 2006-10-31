" a very stripped down versio of cfbolz's algorithm/automaton module "

from pypy.rpython.objectmodel import hint
from pypy.rpython.lltypesystem.lltype import GcArray, Signed, malloc

class LexerError(Exception):
    def __init__(self, input, state, index):
        self.input = input
        self.state = state
        self.index = index
        self.args = (input, state, index)

class DFA(object):
    def __init__(self, num_states=0, transitions=None, final_states=None,
                 names=None):
        self.num_states = 0
        if transitions is None:
            transitions = {}
        if final_states is None:
            final_states = {}
        if names is None:
            names = []
        self.transitions = transitions
        self.final_states = final_states
        self.names = names

    def __repr__(self):
        from pprint import pformat
        return "DFA%s" % (pformat((
            self.num_states, self.transitions, self.final_states,
            self.names)), )

    def add_state(self, name=None, final=False):
        state = self.num_states
        self.num_states += 1
        if final:
            self.final_states[state] = None
        if name is None:
            name = str(state)
        self.names.append(name)
        return self.num_states - 1

    def add_transition(self, state, input, next_state):
        self.transitions[state, input] = next_state

    def get_transition(self, state, input):
        return self.transitions[state, input]

    def contains(self, (state, input)):
        return (state, input) in self.transitions

    def get_all_chars(self):
        all_chars = {}
        for state, input in self.transitions:
            all_chars.add(input)
        return all_chars

    def get_runner(self):
        return DFARunner(self)

def getautomaton():
    # simple example of handcrafted dfa
    a = DFA()
    s0 = a.add_state("start")
    s1 = a.add_state()
    s2 = a.add_state(final=True)
    a.add_transition(s0, "a", s0) 
    a.add_transition(s0, "c", s1) 
    a.add_transition(s0, "b", s2) 
    a.add_transition(s1, "b", s2) 
    return a

def recognize(automaton, s):
    state = 0
    try:
        for char in s:
            state = automaton.get_transition(state, char)
    except KeyError:
        return False

    return state in automaton.final_states

#________________________________________________________________________________

# lower level version - more amenable to JIT

# an earlier version to keep around, based of GcArray

# A = GcArray(Signed, hints={'immutable': True})
# def convertdfa(automaton):
#     automaton.transitions
#     size = automaton.num_states * 256
#     dfatable = malloc(A, size)
#     for ii in range(size):
#         dfatable[ii] = -1
#     for (s, c), r in automaton.transitions.items():
#         dfatable[s * 256 + ord(c)] = r
#     return dfatable

# def recognizetable(dfatable, s):
#     state = 0
#     indx = 0
#     while True:
#         hint(None, global_merge_point=True)
#         if indx >= len(s):
#             break
#         c = s[indx]
#         c = hint(c, promote=True)
#         state = dfatable[state * 256 + ord(c)]
#         hint(state, concrete=True)
#         if state < 0:
#             break
#         indx += 1
#     return hint(state, variable=True)

#________________________________________________________________________________

# another lower level version - more amenable to JIT, this time converts
# nice automata class to a table, represented as a big string 

def convertdfa(automaton):
    automaton.transitions
    size = automaton.num_states * 256
    dfatable = [chr(255)] * size
    for (s, c), r in automaton.transitions.items():
        dfatable[s * 256 + ord(c)] = chr(r)
    return "".join(dfatable)

def recognizetable(dfatable, s):
    state = 0
    indx = 0
    while True:
        hint(None, global_merge_point=True)
        if indx >= len(s):
            break
        c = s[indx]
        c = hint(c, promote=True)
        state = ord(dfatable[state * 256 + ord(c)])
        hint(state, concrete=True)
        if state == 255:
            break
        indx += 1
    return hint(state, variable=True)
