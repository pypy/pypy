from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.function import BuiltinFunction
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace
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
    assert space.interpclass_w(w_x) is x
    assert space.interpclass_w(w_y) is y


def test_simple():
    import py; py.test.skip("in-progress")
    W_MyType.typedef = TypeDef("MyType")
    space = CPyObjSpace()

    def make_mytype():
        return space.wrap(W_MyType(space))
    fn = compile(make_mytype, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res = fn()
    assert type(res).__name__ == 'MyType'
