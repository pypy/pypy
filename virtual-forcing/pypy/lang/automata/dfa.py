" a very stripped down version of cfbolz's algorithm/automaton module "

from pypy.rlib.jit import hint
from pypy.rpython.lltypesystem.lltype import GcArray, Signed, malloc

class DFA(object):
    def __init__(self, num_states=0, transitions=None, final_states=None):
        self.num_states = 0
        self.transitions = {}
        self.final_states = {}

    def add_state(self, final=False):
        state = self.num_states
        self.num_states += 1
        if final:
            self.final_states[state] = None
        return self.num_states - 1

    def add_transition(self, state, input, next_state):
        self.transitions[state, input] = next_state

    def get_transition(self, state, input):
        return self.transitions[state, input]

    def get_language(self):
        all_chars = {}
        for state, input in self.transitions:
            all_chars[input] = None
        return all_chars

    def __repr__(self):
        from pprint import pformat
        return "DFA%s" % (pformat(
            (self.num_states, self.transitions, self.final_states)))

def getautomaton():
    " simple example of handcrafted dfa "
    a = DFA()
    s0 = a.add_state()
    s1 = a.add_state()
    s2 = a.add_state(final=True)
    a.add_transition(s0, "a", s0) 
    a.add_transition(s0, "c", s1) 
    a.add_transition(s0, "b", s2) 
    a.add_transition(s1, "b", s2) 
    return a

def recognize(automaton, s):
    " a simple recognizer "
    state = 0
    try:
        for char in s:
            state = automaton.get_transition(state, char)
    except KeyError:
        return False

    return state in automaton.final_states

def convertdfa(automaton):
    """ converts the dfa transitions into a table, represented as a big string.
    this is just to make the code more amenable to current state of the JIT.  Returns
    a two tuple of dfa as table, and final states"""

    size = automaton.num_states * 256
    dfatable = [chr(255)] * size
    for (s, c), r in automaton.transitions.items():
        dfatable[s * 256 + ord(c)] = chr(r)
    dfatable = "".join(dfatable)
    final_states = "".join([chr(fs) for fs in automaton.final_states])
    return dfatable, final_states

def recognizetable(dfatable, s, finalstates):
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

    # more strange code for now - check final state?
    res = 0
    indx = 0
    while True:
        if indx >= len(finalstates):
            break
        fs = ord(finalstates[indx])
        fs = hint(fs, concrete=True)
        if state == fs:
            res = 1
            break
        indx += 1
    res = hint(res, variable=True)
    return res

def convertagain(automaton):
    alltrans = {}
    for (s, c), r in automaton.transitions.items():
        statetrans = alltrans.setdefault(s, {})
        statetrans[c] = r
    return alltrans, automaton.final_states

def recognizeparts(alltrans, finals, s):
    " a less simple recognizer "
    finals = hint(finals, deepfreeze=True)
    alltrans = hint(alltrans, deepfreeze=True)

    state = 0
    indx = 0
    while indx < len(s):
        hint(None, global_merge_point=True)
        char = s[indx]
        indx += 1
        char = hint(char, promote=True)

        statetrans = alltrans.get(state, None)
        state = statetrans.get(char, -1)
        
        hint(state, concrete=True)
        if state == -1:
            return False
        
    res = state in finals
    res = hint(res, concrete=True)
    res = hint(res, variable=True)
    return res

# a version of recognize() full of hints, but otherwise not too modified

def recognize3(automaton, s):
    automaton = hint(automaton, deepfreeze=True)
    hint(automaton, concrete=True)
    state = 0

    index = 0
    while index < len(s):
        hint(None, global_merge_point=True)
        char = s[index]
        index += 1
        char = hint(char, promote=True)
        try:
            state = automaton.get_transition(state, char)
        except KeyError:
            return False
        state = hint(state, promote=True)

    return state in automaton.final_states
