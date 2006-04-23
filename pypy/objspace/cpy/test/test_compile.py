from pypy.translator.c.test.test_genc import compile
from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace
import pypy.rpython.rctypes.implementation


def test_demo():
    from pypy.module._demo import demo
    space = CPyObjSpace()

    def entry_point(n, w_callable):
        return demo.measuretime(space, n, w_callable)

    fn = compile(entry_point, [int, CPyObjSpace.W_Object],
                 annotatorpolicy = PyPyAnnotatorPolicy())

    res = fn(10, long)
    assert isinstance(res, int)
