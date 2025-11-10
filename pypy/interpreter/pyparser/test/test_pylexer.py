from pypy.interpreter.pyparser.automata import DFA
from pypy.interpreter.pyparser.pylexer import nfaToDfa, notChainStr


def test_notChainStr():
    states = []
    dfa = DFA(*nfaToDfa(states, *notChainStr(states, "abc")))
    assert dfa.recognize("ac") == 1
    assert dfa.recognize("ab") == 2
    assert dfa.recognize("abc") == 2
    assert dfa.recognize("abx") == 2
