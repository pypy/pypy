import autopath
import sys
import py
from py.test import raises

from pypy.translator.tool.cbuild import skip_missing_compiler
from pypy.translator.translator import TranslationContext
from pypy.translator.c import genc

from pypy.rpython.memory.gctransform import GCTransformer

def compile_func(fn, inputtypes):
    t = TranslationContext()
    t.buildannotator().build_types(fn, inputtypes)
    t.buildrtyper().specialize()
#    GCTransformer(t.graphs).transform()
    
    builder = genc.CExtModuleBuilder(t, fn, use_new_funcgen=True)
    builder.generate_source()
    skip_missing_compiler(builder.compile)
    builder.import_module()
    return builder.get_entry_point()


def test_something():
    def f():
        return 1
    fn = compile_func(f, [])
    assert fn() == 1
