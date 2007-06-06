from pypy.lang.prolog.interpreter.compiler import compile
from pypy.lang.prolog.interpreter.term import Atom, Var, Term
from pypy.lang.prolog.interpreter.parsing import get_engine, get_query_and_vars

def test_simple():
    e = get_engine("")
    foo = Atom("foo")
    code = compile(foo, None, e)
    assert not code.opcode
    assert code.opcode_head == "c\x00\x00U"
    assert code.constants == [foo]

def test_simple_withbody():
    e = get_engine("")
    foo = Atom("foo")
    bar = Atom("bar")
    code = compile(foo, bar, e)
    assert code.opcode_head == "c\x00\x00U"
    assert code.opcode == "c\x00\x01D"
    assert code.constants == [foo, bar]

def test_simple_withargs():
    e = get_engine("")
    head, body = get_query_and_vars("f(X) :- g(X).")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "l\x00\x00t\x00\x00U"
    assert code.opcode == "l\x00\x00t\x00\x01D"
    assert code.constants == []
    assert code.term_info == [("f", 1, "f/1"), ("g", 1, "g/1")]

def test_simple_and():
    e = get_engine("")
    head, body = get_query_and_vars("f(X, Y) :- g(X), h(Y).")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "l\x00\x00l\x00\x01t\x00\x00U"
    assert code.opcode == "l\x00\x00t\x00\x01Dl\x00\x01t\x00\x02D"
    assert code.constants == []
    assert code.term_info == [("f", 2, "f/2"), ("g", 1, "g/1"), ("h", 1, "h/1")]

def test_nested_term():
    e = get_engine("")
    head = get_query_and_vars("f(g(X), a).")[0]
    code = compile(head, None, e)
    assert code.opcode_head == "l\x00\x00t\x00\x00c\x00\x00t\x00\x01U"
    assert code.term_info == [("g", 1, "g/1"), ("f", 2, "f/2")]
    assert code.constants == [Atom("a")]

def test_unify():
    e = get_engine("")
    head, body = get_query_and_vars("f(X, Y) :- g(X) = g(Y).")[0].args
    code = compile(head, body, e)
    assert code.opcode_head == "l\x00\x00l\x00\x01t\x00\x00U"
    assert code.opcode == "l\x00\x00t\x00\x01l\x00\x01t\x00\x01U"
    assert code.constants == []
    assert code.term_info == [("f", 2, "f/2"), ("g", 1, "g/1")]


