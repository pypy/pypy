import py
from pypy.lang.prolog.interpreter.error import UnificationFailed
from pypy.lang.prolog.interpreter.term import Atom, Var, Number, Term, Rule
from pypy.lang.prolog.interpreter.engine import Frame, Engine

def test_atom():
    a = Atom("hallo")
    b = Atom("hallo")
    # does not raise
    a.unify(b, None)
    py.test.raises(UnificationFailed, "a.unify(Atom('xxx'), None)")

def test_var():
    b = Var(0)
    frame = Frame()
    frame.clear(1)
    b.unify(Atom("hallo"), frame)
    assert b.getvalue(frame).name == "hallo"
    a = Var(0)
    b = Var(1)
    frame.clear(2)
    a.unify(b, frame)
    a.unify(Atom("hallo"), frame)
    assert a.getvalue(frame).name == "hallo"
    assert b.getvalue(frame).name == "hallo"

def test_unify_var():
    b = Var(0)
    frame = Frame()
    frame.clear(1)
    b.unify(b, frame)
    b.unify(Atom("hallo"), frame)
    py.test.raises(UnificationFailed, b.unify, Atom("bye"), frame)

def test_recursive():
    b = Var(0)
    frame = Frame()
    frame.clear(1)
    b.unify(Term("hallo", [b]), frame)
    

def test_term():
    X = Var(0)
    Y = Var(1)
    t1 = Term("f", [Atom("hallo"), X])
    t2 = Term("f", [Y, Atom("HALLO")])
    frame = Frame()
    frame.clear(2)
    print t1, t2
    t1.unify(t2, frame)
    assert X.getvalue(frame).name == "HALLO"
    assert Y.getvalue(frame).name == "hallo"

def test_run():
    e = Engine()
    e.add_rule(Term("f", [Atom("a"), Atom("b")]))
    e.add_rule(Term("f", [Var(0), Var(0)]))
    e.add_rule(Term(":-", [Term("f", [Var(0), Var(1)]),
                           Term("f", [Var(1), Var(0)])]))
    assert e.run(Term("f", [Atom("b"), Var(0)])) is None
    assert e.frame.getvar(0).name == "b"
    assert e.run(Term("f", [Atom("b"), Atom("a")])) is None


