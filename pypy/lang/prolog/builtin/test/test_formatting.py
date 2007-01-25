from pypy.lang.prolog.builtin import formatting
from pypy.lang.prolog.interpreter.parsing import parse_query_term
from pypy.lang.prolog.interpreter.engine import Engine

def test_list():
    f = formatting.TermFormatter(Engine(), quoted=False, ignore_ops=False)
    t = parse_query_term("[1, 2, 3, 4, 5 | X].")
    assert f.format(t) == "[1, 2, 3, 4, 5|_G0]"
    t = parse_query_term("[a, b, 'A$%%$$'|[]].")
    assert f.format(t) == "[a, b, A$%%$$]"
    t = parse_query_term("'.'(a, b, c).")
    assert f.format(t) == ".(a, b, c)"

def test_op_formatting():
    f = formatting.TermFormatter(Engine(), quoted=False, ignore_ops=False)
    t = parse_query_term("'+'(1, 2).")
    assert f.format(t) == "1+2"
    t = parse_query_term("'+'(1, *(3, 2)).")
    assert f.format(t) == "1+3*2"
    t = parse_query_term("'*'(1, *(3, 2)).")
    assert f.format(t) == "1*(3*2)"

def test_atom_formatting():
    f = formatting.TermFormatter(Engine(), quoted=False, ignore_ops=False)
    t = parse_query_term("'abc def'.")
    assert f.format(t) == "abc def"
    f = formatting.TermFormatter(Engine(), quoted=True, ignore_ops=False)
    t = parse_query_term("'abc def'.")
    assert f.format(t) == "'abc def'"
    t = parse_query_term("abc.")
    assert f.format(t) == "abc"

