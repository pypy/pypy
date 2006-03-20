from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.c import exceptiontransform
from pypy.objspace.flow.model import c_last_exception

from pypy import conftest

def transform_func(fn, inputtypes):
    t = TranslationContext()
    t.buildannotator().build_types(fn, inputtypes)
    t.buildrtyper().specialize()
    if conftest.option.view:
        t.view()
    g = graphof(t, fn)
    etrafo = exceptiontransform.ExceptionTransformer(t)
    etrafo.create_exception_handling(g)
    if conftest.option.view:
        t.view()
    return t, g

def test_simple():
    def one():
        return 1
    
    def foo():
        one()
        one()

    t, g = transform_func(foo, [])
    assert len(list(g.iterblocks())) == 2 # graph does not change 
    
def test_raises():
    def one(x):
        if x:
            raise ValueError()

    def foo():
        one(0)
        one(1)
    t, g = transform_func(foo, [])
    assert len(list(g.iterblocks())) == 5

