from pypy.interpreter.pyparser.pylexer import *

def test_extremely_simple():
    states = []
    res = group(states,
                chainStr(states, "ab"),
                chainStr(states, 'abc'))
    dfa = nfaToDfa(states, *res)
    assert dfa == ([{'a': 1}, {'b': 2}, {'c': 3}, {}], [False, False, True, True])

