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
    b = Var(0)
    heap = Heap()
    heap.clear(1)
    b.unify(Atom.newatom("hallo"), heap)
    assert b.getvalue(heap).name == "hallo"
    a = Var(0)
    b = Var(1)
    heap.clear(2)
    a.unify(b, heap)
    a.unify(Atom.newatom("hallo"), heap)
    assert a.getvalue(heap).name == "hallo"
    assert b.getvalue(heap).name == "hallo"

def test_unify_var():
    b = Var(0)
    heap = Heap()
    heap.clear(1)
    b.unify(b, heap)
    b.unify(Atom.newatom("hallo"), heap)
    py.test.raises(UnificationFailed, b.unify, Atom.newatom("bye"), heap)

def test_recursive():
    b = Var(0)
    heap = Heap()
    heap.clear(1)
    b.unify(Term("hallo", [b]), heap)
    

def test_term():
    X = Var(0)
    Y = Var(1)
    t1 = Term("f", [Atom.newatom("hallo"), X])
    t2 = Term("f", [Y, Atom.newatom("HALLO")])
    heap = Heap()
    heap.clear(2)
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
    e.add_rule(Term("f", [Var(0), Var(0)]))
    e.add_rule(Term(":-", [Term("f", [Var(0), Var(1)]),
                           Term("f", [Var(1), Var(0)])]))
    X = e.heap.newvar()
    assert e.run(Term("f", [Atom.newatom("b"), X])) is None
    assert X.dereference(e.heap).name == "b"
    assert e.run(Term("f", [Atom.newatom("b"), Atom.newatom("a")])) is None


