from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.interpreter.function import BuiltinFunction
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root


def test_builtin_function():
    def entrypoint(space, w_x):
        x = space.int_w(w_x)
        result = x * 7
        return space.wrap(result)
    entrypoint.unwrap_spec = [ObjSpace, W_Root]

    space = CPyObjSpace()
    func = interp2app(entrypoint).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_entrypoint = space.wrap(bltin)
    w_result = space.call_function(w_entrypoint, space.wrap(-2))
    result = space.int_w(w_result)
    assert result == -14
