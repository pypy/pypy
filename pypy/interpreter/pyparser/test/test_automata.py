from pypy.interpreter.pyparser.automata import DFA, DEFAULT

def test_states():
    d = DFA([{"\x00": 1}, {"\x01": 0}], [False, True])
    assert d.states == "\x01\xff\xff\x00"
    assert d.defaults == "\xff\xff"
    assert d.max_char == 2

    d = DFA([{"\x00": 1}, {DEFAULT: 0}], [False, True])
    assert d.states == "\x01\x00"
    assert d.defaults == "\xff\x00"
    assert d.max_char == 1
