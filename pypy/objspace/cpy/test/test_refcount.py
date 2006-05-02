import sys
from pypy.translator.c.test.test_genc import compile
from pypy.objspace.cpy.refcount import *


def test_reftricks():
    x = object()
    w_x = W_Object(x)
    before = sys.getrefcount(x)
    Py_Incref(w_x)
    after = sys.getrefcount(x)
    assert after == before+1
    assert w_x.value is x

    Py_Decref(w_x)
    after = sys.getrefcount(x)
    assert after == before
    assert w_x.value is x


def test_compile_reftricks():
    def func(obj, flag):
        w = W_Object(obj)
        if flag > 0:
            Py_Incref(w)
        else:
            Py_Decref(w)

    fn = compile(func, [object, int])

    x = object()
    before = sys.getrefcount(x)
    fn(x, +1)
    after = sys.getrefcount(x)
    assert after == before+1

    fn(x, -1)
    after = sys.getrefcount(x)
    assert after == before
