import autopath
from pypy.translator.translator import TranslationContext

"""
This is a simple approach to support building extension moduels.
Tnbe key idea is to provide a mechanism to record certain objects
and types to be recognized as SomeObject, to be created using imports
without trying to further investigate them.

This is intentionally using global dicts, since what we can
translate is growing in time, but usually nothing you want
to configure dynamically.
"""

def get_annotation(func):
    argstypelist = []
    if func.func_defaults:
        for spec in func.func_defaults:
            if isinstance(spec, tuple):
                # use the first type only for the tests
                spec = spec[0]
            argstypelist.append(spec)
    return argstypelist

def getcompiled(func, view=False, inline_threshold=1, use_boehm=False):
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

def example_long(arg=int):
    return long(arg+42)

def test_long():
    f = getcompiled(example_long)
    assert example_long(10) == f(10)
