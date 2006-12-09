import autopath
from pypy.translator.translator import TranslationContext
from pypy import conftest
from py.test import raises

# see annotation/registry for comments

def get_annotation(func):
    argstypelist = []
    if func.func_defaults:
        for spec in func.func_defaults:
            if isinstance(spec, tuple):
                # use the first type only for the tests
                spec = spec[0]
            argstypelist.append(spec)
    missing = [object] * (func.func_code.co_argcount - len(argstypelist))
    return missing + argstypelist

def getcompiled(func, view=conftest.option.view, inline_threshold=1, use_boehm=False):
    from pypy.translator.translator import TranslationContext
    from pypy.translator.backendopt.all import backend_optimizations

    from pypy.translator.c import gc
    from pypy.translator.c.genc import CExtModuleBuilder

    global t # allow us to view later
    t = TranslationContext()
    t.buildannotator().build_types(func, get_annotation(func))
    t.buildrtyper().specialize()
    t.checkgraphs()

    gcpolicy = None
    if use_boehm:
        gcpolicy = gc.BoehmGcPolicy

    cbuilder = CExtModuleBuilder(t, func, gcpolicy=gcpolicy)
    cbuilder.generate_source()
    cbuilder.compile()

    backend_optimizations(t, inline_threshold=inline_threshold)
    if view:
        t.viewcg()
    return getattr(cbuilder.import_module(), func.__name__)

def example_int_long(arg=int):
    return long(arg+42)

def example_obj_long(arg):
    return long(arg+42)

def test_long():
    f = getcompiled(example_int_long)
    assert example_int_long(10) == f(10)
    g = getcompiled(example_obj_long)
    assert example_obj_long(10) == f(10)
    bigval = 123456789012345l
    assert raises(OverflowError, f, bigval)
    assert g(bigval) == example_obj_long(bigval)
    assert g(float(bigval)) == example_obj_long(bigval)
    assert raises(TypeError, g, str(bigval))
