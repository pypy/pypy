from pypy.interpreter.pyparser.automata import DFA
from pypy.interpreter.pyparser.gendfa import output

def test_states():
    states = [{"\x00": 1}, {"\x01": 0}]
    d = DFA(states[:], [False, True])
    assert output('test', d, states) == """\
accepts = [False, True]
states = [
    # 0
    {'\\x00': 1},
    # 1
    {'\\x01': 0},
    ]
test = automata.DFA(states, accepts)
"""
