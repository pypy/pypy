from pypy.objspace.cpy.objspace import CPyObjSpace
from pypy.tool.pytest.appsupport import raises_w
from pypy.interpreter.function import BuiltinFunction
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy.interpreter.argument import Arguments


def entrypoint1(space, w_x):
    x = space.int_w(w_x)
    result = x * 7
    return space.wrap(result)
entrypoint1.unwrap_spec = [ObjSpace, W_Root]

def entrypoint2(space, w_x):
    pass
entrypoint2.unwrap_spec = [ObjSpace, W_Root]

def entrypoint3(space, w_x, args_w):
    x = space.int_w(w_x)
    result = x * len(args_w)
    return space.wrap(result)
entrypoint3.unwrap_spec = [ObjSpace, W_Root, 'args_w']


def test_builtin_function():
    space = CPyObjSpace()
    func = interp2app(entrypoint1).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_entrypoint = space.wrap(bltin)
    w_result = space.call_function(w_entrypoint, space.wrap(-2))
    result = space.int_w(w_result)
    assert result == -14

def test_builtin_function_keywords():
    space = CPyObjSpace()
    func = interp2app(entrypoint1).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_entrypoint = space.wrap(bltin)
    args = Arguments(space, [], {'x': space.wrap(-3)})
    w_result = space.call_args(w_entrypoint, args)
    result = space.int_w(w_result)
    assert result == -21

def test_exception():
    space = CPyObjSpace()
    func = interp2app(entrypoint1).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_entrypoint = space.wrap(bltin)
    w1 = space.wrap('not an int')
    raises_w(space, space.w_TypeError, space.call_function, w_entrypoint, w1)

def test_None_result():
    space = CPyObjSpace()
    func = interp2app(entrypoint2).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_entrypoint = space.wrap(bltin)
    w_result = space.call_function(w_entrypoint, space.wrap(-2))
    assert space.is_w(w_result, space.wrap(None))

def test_star_args():
    space = CPyObjSpace()
    func = interp2app(entrypoint3).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_entrypoint = space.wrap(bltin)
    w_result = space.call_function(w_entrypoint, space.wrap(-2),
                                                 space.wrap("hello"),
                                                 space.wrap("world"))
    result = space.int_w(w_result)
    assert result == -4

def test_star_args_no_args():
    space = CPyObjSpace()
    func = interp2app(entrypoint3).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_entrypoint = space.wrap(bltin)
    w_result = space.call_function(w_entrypoint, space.wrap(-2))
    result = space.int_w(w_result)
    assert result == 0
