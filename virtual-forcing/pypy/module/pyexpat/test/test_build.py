from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.annotation.listdef import s_list_of_strings
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool.rffi_platform import CompilationError

import os, pyexpat
import py

try:
   from pypy.module.pyexpat import interp_pyexpat
except (ImportError, CompilationError):
    py.test.skip("Expat not installed")

def test_build():
    def entry_point(argv):
        res = interp_pyexpat.XML_ErrorString(3)
        os.write(1, rffi.charp2str(res))
        return 0

    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()

    builder = CStandaloneBuilder(t, entry_point, t.config)
    builder.generate_source()
    builder.compile()
    data = builder.cmdexec()
    assert data == pyexpat.ErrorString(3)
