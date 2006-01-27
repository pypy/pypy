import autopath
import sys
import py
from py.test import raises

from pypy.translator.tool.cbuild import skip_missing_compiler
from pypy.translator.translator import TranslationContext
from pypy.translator.c import genc, newgc
from pypy.rpython.lltypesystem import lltype

from pypy.rpython.memory.gctransform import GCTransformer

def compile_func(fn, inputtypes):
    t = TranslationContext()
    t.buildannotator().build_types(fn, inputtypes)
    t.buildrtyper().specialize()
    GCTransformer(t.graphs).transform()
    
    builder = genc.CExtModuleBuilder(t, fn, use_new_funcgen=True,
                                     gcpolicy=newgc.RefcountingGcPolicy)
    builder.generate_source()
    skip_missing_compiler(builder.compile)
    builder.import_module()
    return builder.get_entry_point()


def test_something():
    def f():
        return 1
    fn = compile_func(f, [])
    assert fn() == 1

def test_something_more():
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(x):
        s = lltype.malloc(S)
        s.x = x
        return s.x
    fn = compile_func(f, [int])
    assert fn(1) == 1
