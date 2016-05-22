from pypy.interpreter.pyparser.automata import DFA, DEFAULT
from pypy.interpreter.pyparser.genpytokenize import output

def test_states():
    d = DFA([{"\x00": 1}, {"\x01": 0}], [False, True])
    assert output('test', DFA, d) == """\
accepts = [False, True]
states = [
    ]
test = automata.pypy.interpreter.pyparser.automata.DFA(states, accepts)

"""
