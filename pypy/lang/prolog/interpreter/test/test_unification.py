import py
from pypy.lang.prolog.interpreter.error import UnificationFailed
from pypy.lang.prolog.interpreter.term import Atom, Var, Number, Term, BlackBox
from pypy.lang.prolog.interpreter.engine import Heap, Engine

def test_atom():
    a = Atom.newatom("hallo")
    b = Atom.newatom("hallo")
    # does not raise
    a.unify(b, None)
    py.test.raises(UnificationFailed, "a.unify(Atom.newatom('xxx'), None)")

def test_var():
    b = Var()
    heap = Heap()
    b.unify(Atom.newatom("hallo"), heap)
    assert b.getvalue(heap).name == "hallo"
    a = Var()
    b = Var()
    a.unify(b, heap)
    a.unify(Atom.newatom("hallo"), heap)
    assert a.getvalue(heap).name == "hallo"
    assert b.getvalue(heap).name == "hallo"

def test_unify_var():
    b = Var()
    heap = Heap()
    b.unify(b, heap)
    b.unify(Atom.newatom("hallo"), heap)
    py.test.raises(UnificationFailed, b.unify, Atom.newatom("bye"), heap)

def test_recursive():
    b = Var()
    heap = Heap()
    b.unify(Term("hallo", [b]), heap)

def test_term():
    X = Var()
    Y = Var()
    t1 = Term("f", [Atom.newatom("hallo"), X])
    t2 = Term("f", [Y, Atom.newatom("HALLO")])
    heap = Heap()
    print t1, t2
    t1.unify(t2, heap)
    assert X.getvalue(heap).name == "HALLO"
    assert Y.getvalue(heap).name == "hallo"

def test_blackbox():
    bl1 = BlackBox()
    bl2 = BlackBox()
    heap = Heap()
    bl1.unify(bl1, heap)
    py.test.raises(UnificationFailed, bl1.unify, bl2, heap)

def test_run():
    e = Engine()
    e.add_rule(Term("f", [Atom.newatom("a"), Atom.newatom("b")]))
    X = Var()
    Y = Var()
    e.add_rule(Term("f", [X, X]))
    e.add_rule(Term(":-", [Term("f", [X, Y]),
                           Term("f", [Y, X])]))
    X = e.heap.newvar()
    e.run(Term("f", [Atom.newatom("b"), X]))
    assert X.dereference(e.heap).name == "b"
    e.run(Term("f", [Atom.newatom("b"), Atom.newatom("a")]))


