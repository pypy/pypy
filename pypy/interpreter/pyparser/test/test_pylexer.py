from pypy.interpreter.pyparser.pylexer import *

def test_extremely_simple():
    states = []
    res = group(states,
                chainStr(states, "ab"),
                chainStr(states, 'abc'))
    dfa = nfaToDfa(states, *res)
    assert dfa == ([{'a': 1}, {'b': 2}, {'c': 3}, {}], [False, False, True, True])

def test_labels():
    states = []
    startab, endab = chainStr(states, "ab")
    startabc, endabc = chainStr(states, 'abc')
    res = group(states, (startab, endab), (startabc, endabc))
    labels = {endab: "ab", endabc: "abc"}
    dfa = nfaToDfa(states, res[0], labels)
    assert dfa == ([{'a': 1}, {'b': 2}, {'c': 3}, {}],
                   [frozenset([]), frozenset([]), frozenset(['ab']), frozenset(['abc'])])

def test_dont_merge_labels():

    states = []
    startab, endab = chainStr(states, "if")
    name = chain(states,
                 groupStr(states, "abcif" + "_"),
                 any(states, groupStr(states,
                                      "abcif0123_")))
    res = group(states, (startab, endab), name)
    labels = {endab: "if", name[1]: "name"}
    dfa = nfaToDfa(states, res[0], labels)
    assert dfa == (
        [{'i': 1, 'a': 2, 'b': 2, 'c': 2, 'f': 2, '_': 2},
         {'f': 3, 'a': 2, 'b': 2, 'c': 2, 'i': 2, '0': 2, '1': 2, '2': 2, '3': 2, '_': 2},
         {'a': 2, 'b': 2, 'c': 2, 'i': 2, 'f': 2, '0': 2, '1': 2, '2': 2, '3': 2, '_': 2},
         {'a': 2, 'b': 2, 'c': 2, 'i': 2, 'f': 2, '0': 2, '1': 2, '2': 2, '3': 2, '_': 2}],
        [frozenset([]), frozenset(['name']), frozenset(['name']), frozenset(['if', 'name'])])

def test_python_keywords_and_names():
    import string
    from pypy.interpreter.pyparser.pygram import python_grammar
    from pypy.interpreter.pyparser.automata import DFA
    states = []
    name = chain(states,
                 groupStr(states, string.letters + "_"),
                 any(states, groupStr(states,
                                      string.letters + string.digits + "_")))
    labels = {name[1]: "NAME"}
    keywords = []
    for keyword in python_grammar.keyword_ids:
        keywords.append(chainStr(states, keyword))
        labels[keywords[-1][1]] = keyword
    res = group(states, name, *keywords)
    dfa = nfaToDfa(states, res[0], labels)
    aut = DFA(dfa[0], [bool(x) for x in dfa[1]])
    for keyword in python_grammar.keyword_ids:
        res = aut.recognize(keyword)
        assert res == len(keyword)
        assert keyword in dfa[1][aut.last_state]
    for name in ["ABC", "_01231", "ifs"]:
        res = aut.recognize(name)
        assert res == len(name)
        assert "NAME" in dfa[1][aut.last_state]
