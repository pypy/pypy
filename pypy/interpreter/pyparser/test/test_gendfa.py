import pytest
from pypy.interpreter.pyparser.automata import DFA
from pypy.interpreter.pyparser.gendfa import output, makePyEndDFA

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


@pytest.mark.parametrize("s", ("{", "}", "\\{"))
def test_f_string_stop_on_braces(s):
    for i, c in enumerate(s):
        if c in "{}":
            break
    else:
        pytest.fail("Missing brace in input")

    d, _ = makePyEndDFA('"', f_str=True)
    assert d.recognize(s) == i+1
