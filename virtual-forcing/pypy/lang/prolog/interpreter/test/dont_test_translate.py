from pypy.translator.interactive import Translation
from pypy.rpython.test.test_llinterp import interpret
from pypy.lang.prolog.interpreter import parsing
from pypy.lang.prolog.interpreter.term import Atom
from pypy.lang.prolog.interpreter.test.tool import *

from pypy.lang.prolog.interpreter.conftest import option
if not option.slow:
    py.test.skip("slow tests")

def test_parser():
    def f(x):
        if x:
            s = "a(X, Y, Z)."
        else:
            s = "f(a, X, _, _, X, f(X, 2.455))."
        term = parsing.parse_file(s)
        assert isinstance(term, parsing.Nonterminal)
        return term.symbol
    assert f(True) == "file"
    assert f(True) == "file"
    t = Translation(f)
    t.annotate([bool])
    t.rtype()
    t.backendopt()
    func = t.compile_c()
    assert func(True) == "file"
    assert func(False) == "file"

def test_engine():
    e = get_engine("""
        g(a, a).
        g(a, b).
        g(b, c).
        f(X, Z) :- g(X, Y), g(Y, Z).
    """)
    t1 = parse_query_term("f(a, c).")
    t2 = parse_query_term("f(X, c).")
    def run():
        e.run(t1)
        e.run(t2)
        v0 = e.heap.getvar(0)
        if isinstance(v0, Atom):
            return v0.name
        return "no!"
    assert run() == "a"
    t = Translation(run)
    t.annotate()
    t.rtype()
    func = t.compile_c()
    assert func() == "a"
