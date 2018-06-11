from pypy.interpreter.pyparser.automata import DFA, NonGreedyDFA, DEFAULT

def test_states():
    d = DFA([{"\x00": 1}, {"\x01": 0}], [False, True])
    assert d.states == "\x01\xff\xff\x00"
    assert d.defaults == "\xff\xff"
    assert d.max_char == 2

    d = DFA([{"\x00": 1}, {DEFAULT: 0}], [False, True])
    assert d.states == "\x01\x00"
    assert d.defaults == "\xff\x00"
    assert d.max_char == 1

def test_recognize():
    d = DFA([{"a": 1}, {"b": 0}], [False, True])
    assert d.recognize("ababab") == 5
    assert d.recognize("c") == -1

    d = DFA([{"a": 1}, {DEFAULT: 0}], [False, True])
    assert d.recognize("a,a?ab") == 5
    assert d.recognize("c") == -1

    d = NonGreedyDFA([{"a": 1}, {"b": 0}], [False, True])
    assert d.recognize("ababab") == 1
    assert d.recognize("c") == -1

    d = NonGreedyDFA([{"a": 1}, {DEFAULT: 0}], [False, True])
    assert d.recognize("a,a?ab") == 1
    assert d.recognize("c") == -1
