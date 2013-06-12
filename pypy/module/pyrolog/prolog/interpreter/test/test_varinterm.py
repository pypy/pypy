import py
from prolog.interpreter.term import Callable, BindingVar, VarInTerm, NumberedVar, UnificationFailed
from prolog.interpreter.heap import Heap
from prolog.interpreter.continuation import Engine
from prolog.interpreter.test.tool import assert_true
py.test.skip("disabled for now")

def test_copy_standardize_apart():
    h = Heap()
    t = Callable.build("a", [Callable.build("b"), NumberedVar(0)])
    res = t.copy_standardize_apart(h, [None])
    assert res.argument_at(1).parent_or_binding is res
    assert not res.argument_at(1).bound
    assert res.argument_at(1).__class__.__name__ == "VarInTerm1"

def test_varinterm_bind():
    h = Heap()
    t = Callable.build("a", [Callable.build("b"), NumberedVar(0)])
    res = t.copy_standardize_apart(h, [None])
    v = res.argument_at(1)
    v.unify(Callable.build("c"), h)
    assert res.argument_at(1).name() == "c"
    assert v.parent_or_binding.name() == "c"
    assert v.bound

def test_varinterm_bind_again():
    h = Heap()
    t = Callable.build("a", [Callable.build("b"), NumberedVar(0)])
    res = t.copy_standardize_apart(h, [None])
    v = res.argument_at(1)
    v.unify(Callable.build("c"), h)
    py.test.raises(UnificationFailed, v.unify, Callable.build("d"), h)


def test_varinterm_bind_later():
    h = Heap()
    t = Callable.build("a", [Callable.build("b"), NumberedVar(0)])
    res = t.copy_standardize_apart(h, [None])
    h2 = h.branch()
    v = res.argument_at(1)
    assert v.dereference(h2) is v
    v.unify(Callable.build("c"), h2)
    assert res.argument_at(1).dereference(h2).name() == "c"

    h2.revert_upto(h)

    v2 = res.argument_at(1)
    assert v2.dereference(h2) is v2
    v.dereference(h2) is v2

    v.unify(Callable.build("d"), h2)
    assert res.argument_at(1).dereference(h2).name() == "d"

def test_functional_test():
    e = Engine(load_system=True)
    env = assert_true("append([1, 2, 3, 4, 5], [2, 3, 4, 5, 6], X).", e)
    res = env['X']
    l = []
    while res.name() == ".":
        l.append(res.argument_at(0).num)
        res = res.argument_at(1)
    assert l == [1, 2, 3, 4, 5, 2, 3, 4, 5, 6]

