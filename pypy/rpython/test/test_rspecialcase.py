from pypy.rpython.lltype import *
from pypy.rpython.test.test_llinterp import interpret

from pypy.translator.ann_override import PyPyAnnotatorPolicy
from pypy.interpreter.typedef import instantiate


def test_instantiate():
    class A:
        pass
    def f():
        return instantiate(A)
    res = interpret(f, [], policy=PyPyAnnotatorPolicy())
    assert res.super.typeptr.name[0] == 'A'
