import py
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.function import BuiltinFunction
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace, W_Object
from pypy.translator.c.test.test_genc import compile


class W_MyType(Wrappable):
    def __init__(self, space):
        self.space = space


def test_direct():
    W_MyType.typedef = TypeDef("MyType")
    space = CPyObjSpace()
    x = W_MyType(space)
    y = W_MyType(space)
    w_x = space.wrap(x)
    w_y = space.wrap(y)
    assert space.interp_w(W_MyType, w_x) is x
    assert space.interp_w(W_MyType, w_y) is y
    py.test.raises(OperationError, "space.interp_w(W_MyType, space.wrap(42))")


def test_get_blackbox():
    W_MyType.typedef = TypeDef("MyType")
    space = CPyObjSpace()

    def make_mytype():
        return space.wrap(W_MyType(space))
    fn = compile(make_mytype, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res = fn(expected_extra_mallocs=1)
    assert type(res).__name__ == 'MyType'


def test_blackbox():
    W_MyType.typedef = TypeDef("MyType")
    space = CPyObjSpace()

    def mytest(w_myobj):
        myobj = space.interp_w(W_MyType, w_myobj, can_be_None=True)
        if myobj is None:
            myobj = W_MyType(space)
            myobj.abc = 1
        myobj.abc *= 2
        w_myobj = space.wrap(myobj)
        w_abc = space.wrap(myobj.abc)
        return space.newtuple([w_myobj, w_abc])

    def fn(obj):
        w_obj = W_Object(obj)
        w_res = mytest(w_obj)
        return w_res.value
    fn.allow_someobjects = True

    fn = compile(fn, [object],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res, abc = fn(None, expected_extra_mallocs=1)
    assert abc == 2
    assert type(res).__name__ == 'MyType'

    res2, abc = fn(res, expected_extra_mallocs=1)
    assert abc == 4
    assert res2 is res

    res2, abc = fn(res, expected_extra_mallocs=1)
    assert abc == 8
    assert res2 is res

    res2, abc = fn(res, expected_extra_mallocs=1)
    assert abc == 16
    assert res2 is res
