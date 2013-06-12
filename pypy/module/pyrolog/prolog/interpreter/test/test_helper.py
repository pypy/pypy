import py
from prolog.interpreter.helper import convert_to_str, unwrap_list
from prolog.interpreter.term import Callable, BigInt, BindingVar, Atom
from prolog.interpreter.heap import Heap
from rpython.rlib.rbigint import rbigint

def test_convert_to_str():
    assert "a" == convert_to_str(Callable.build("a"))
    assert "100" == convert_to_str(Callable.build("100"))
    assert "1000.111" == convert_to_str(Callable.build("1000.111"))
    assert ("100000000000000000000" == 
            convert_to_str(Callable.build("100000000000000000000")))
    assert "1" == convert_to_str(BigInt(rbigint.fromint(1)))
    assert ("-1000000000000000" == 
            convert_to_str(BigInt(rbigint.fromdecimalstr("-1000000000000000"))))

def test_unwrap_list():
    a = Callable.build("a")
    l = unwrap_list(Callable.build(".", 
            [a, Callable.build("[]")]))
    assert len(l) == 1
    assert l[0] is a

    v1 = BindingVar()
    a1 = Callable.build("a")
    l1 = unwrap_list(Callable.build(".",
            [v1, Callable.build(".", [a1, Callable.build("[]")])]))
    assert l1 == [v1, a1]

    empty = Callable.build("[]")
    v2 = BindingVar()
    l2 = Callable.build(".", [a, v2])
    v2.unify(empty, Heap())
    unwrapped = unwrap_list(l2)
    assert unwrapped == [a]

    v3 = BindingVar()
    v4 = BindingVar()
    b = Callable.build("b")
    h = Heap()
    l3 = Callable.build(".", [a, v3])
    v3.unify(Callable.build(".", [b, v4]), h)
    v4.unify(Callable.build("[]"), h)
    unwrapped2 = unwrap_list(l3)
    assert unwrapped2 == [a, b]
