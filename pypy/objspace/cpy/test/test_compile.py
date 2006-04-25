import py
from pypy.translator.c.test.test_genc import compile
from pypy.annotation.annrpython import RPythonAnnotator
from pypy.translator.translator import TranslationContext, graphof
from pypy.objspace.cpy.ann_policy import CPyAnnotatorPolicy
from pypy.objspace.cpy.objspace import CPyObjSpace
import pypy.rpython.rctypes.implementation
from pypy.interpreter.function import BuiltinFunction
from pypy.interpreter.gateway import interp2app, ObjSpace, W_Root
from pypy import conftest


def test_demo():
    from pypy.module._demo import demo
    space = CPyObjSpace()

    def entry_point(n, w_callable):
        return demo.measuretime(space, n, w_callable)

    fn = compile(entry_point, [int, CPyObjSpace.W_Object],
                 annotatorpolicy = CPyAnnotatorPolicy())

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
    return entrypoint

def test_annotate_bltinfunc():
    entrypoint = maketest()
    t = TranslationContext()
    a = t.buildannotator(policy=CPyAnnotatorPolicy())
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

def test_compile_bltinfunc():
    entrypoint = maketest()
    fn = compile(entrypoint, [int],
                 annotatorpolicy = CPyAnnotatorPolicy())
    res = fn(-6)
    assert res == -42
