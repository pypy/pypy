import py
from pypy.translator.c.test.test_genc import compile
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext, graphof
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace
import pypy.rpython.rctypes.implementation
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import BuiltinFunction
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy import conftest


def test_simple_demo():
    from pypy.module._demo import demo
    space = CPyObjSpace()

    def entry_point(n, w_callable):
        return demo.measuretime(space, n, w_callable)

    fn = compile(entry_point, [int, CPyObjSpace.W_Object],
                 annotatorpolicy = CPyAnnotatorPolicy(space))

    res = fn(10, long)
    assert isinstance(res, int)

# ____________________________________________________________

def myfunc(space, w_x):
    x = space.int_w(w_x)
    result = x * 7
    return space.wrap(result)
myfunc.unwrap_spec = [ObjSpace, W_Root]

def maketest():
    space = CPyObjSpace()
    func = interp2app(myfunc).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_myfunc = space.wrap(bltin)
    def entrypoint(n):
        w_result = space.call_function(w_myfunc, space.wrap(n))
        return space.int_w(w_result)
    return space, entrypoint

def test_annotate_bltinfunc():
    space, entrypoint = maketest()
    t = TranslationContext()
    a = t.buildannotator(policy=CPyAnnotatorPolicy(space))
    s = a.build_types(entrypoint, [int])
    if conftest.option.view:
        t.view()
    assert s.knowntype == int
    graph = graphof(t, myfunc)
    assert len(graph.getargs()) == 2
    s = a.binding(graph.getargs()[1])
    assert s.knowntype == CPyObjSpace.W_Object
    s = a.binding(graph.getreturnvar())
    assert s.knowntype == CPyObjSpace.W_Object

def test_annotate_indirect():
    space = CPyObjSpace()
    func = interp2app(myfunc).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_myfunc = space.wrap(bltin)
    w_mylist = space.newlist([w_myfunc])
    def entrypoint():
        return w_mylist
    t = TranslationContext()
    a = t.buildannotator(policy=CPyAnnotatorPolicy(space))
    s = a.build_types(entrypoint, [])
    if conftest.option.view:
        t.view()
    # 'myfunc' should still have been annotated
    graph = graphof(t, myfunc)
    assert len(graph.getargs()) == 2
    s = a.binding(graph.getargs()[1])
    assert s.knowntype == CPyObjSpace.W_Object
    s = a.binding(graph.getreturnvar())
    assert s.knowntype == CPyObjSpace.W_Object

def test_compile_bltinfunc():
    space, entrypoint = maketest()
    fn = compile(entrypoint, [int],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn(-6)
    assert res == -42

# ____________________________________________________________

def makedemotest():
    from pypy.module._demo import demo
    space = CPyObjSpace()
    func = interp2app(demo.measuretime).__spacebind__(space)
    bltin = BuiltinFunction(func)
    w_measuretime = space.wrap(bltin)
    def entrypoint(n, w_callable):
        w_result = space.call_function(w_measuretime, space.wrap(n),
                                                      w_callable)
        return space.int_w(w_result)
    return space, entrypoint

def test_compile_demo():
    space, entrypoint = makedemotest()
    fn = compile(entrypoint, [int, CPyObjSpace.W_Object],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    res = fn(10, complex)
    assert isinstance(res, int)

# ____________________________________________________________

def test_compile_exception_to_rpython():
    space = CPyObjSpace()
    def entrypoint(n):
        w_sys = space.getbuiltinmodule('sys')
        w_n = space.wrap(n)
        try:
            space.call_method(w_sys, 'exit', w_n)
        except OperationError, e:
            # a bit fragile: this test assumes that the OperationError
            # is *not* normalized
            return space.newtuple([e.w_type, e.w_value])
        else:
            return space.wrap('did not raise??')

    fn = compile(entrypoint, [int],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    result = fn(5)
    assert result == (SystemExit, 5)

def test_compile_exception_from_rpython():
    space = CPyObjSpace()
    w_SystemExit = space.W_Object(SystemExit)
    def myfunc(n):
        if n > 0:
            raise OperationError(w_SystemExit, space.wrap(n))
        else:
            return space.wrap(n)
    myfunc.unwrap_spec = [int]
    w_myfunc = space.wrap(interp2app(myfunc))

    def entrypoint():
        return w_myfunc

    fn = compile(entrypoint, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    myfunc1 = fn()
    e = py.test.raises(SystemExit, myfunc1, 5)
    ex = e.value
    assert ex.args == (5,)

def test_compile_exception_through_rpython():
    space = CPyObjSpace()
    def myfunc(n):
        w_sys = space.getbuiltinmodule('sys')
        w_n = space.wrap(n)
        space.call_method(w_sys, 'exit', w_n)
        return space.w_None   # should not actually reach this point
    myfunc.unwrap_spec = [int]
    w_myfunc = space.wrap(interp2app(myfunc))

    def entrypoint():
        return w_myfunc

    fn = compile(entrypoint, [],
                 annotatorpolicy = CPyAnnotatorPolicy(space))
    myfunc1 = fn()
    e = py.test.raises(SystemExit, myfunc1, 5)
    ex = e.value
    assert ex.args == (5,)
