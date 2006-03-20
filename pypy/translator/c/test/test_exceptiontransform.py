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
    exceptiontransform.create_exception_handling(t, g)
    if conftest.option.view:
        t.view()
    for b in g.iterblocks():
        l = len(b.operations)
        for i in range(l):
            op = b.operations[i]
            if op.opname == 'direct_call':
                assert i == l-1
                assert b.exitswitch is c_last_exception
    return t, g

def test_simple():
    def one():
        return 1
    
    def foo():
        one()
        one()

    t, g = transform_func(foo, [])
    
    
        
