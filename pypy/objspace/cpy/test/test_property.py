from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.interpreter.typedef import GetSetProperty


def test_property():
    space = CPyObjSpace()
    def func(space, w_a):
        return space.getattr(w_a, space.wrap('__name__'))
    name_getter = GetSetProperty(func)
    w_name_getter = space.wrap(name_getter)
    w_result = space.call_method(w_name_getter, '__get__', space.w_int)
    result = space.str_w(w_result)
    assert result == 'int'
