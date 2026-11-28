from rpython.translator.translator import TranslationContext
from rpython.translator.c.genc import CStandaloneBuilder
from rpython.annotator.listdef import s_list_of_strings
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool.rffi_platform import CompilationError
from rpython.rlib.rarithmetic import intmask

import os
import py
try:
    import pyexpat
except ImportError:
    py.test.skip("No module expat", allow_module_level=True)

try:
    from pypy.module.pyexpat import interp_pyexpat
except (ImportError, CompilationError):
    py.test.skip("Expat not installed", allow_module_level=True)

def test_build():
    def entry_point(argv):
        parser = interp_pyexpat.XML_ParserCreate("utf-8")
        with rffi.scoped_str2charp("<a>\n  <b/>\n</c>") as buf:
            interp_pyexpat.XML_Parse(parser, buf, 15, 1)
        line = interp_pyexpat.XML_GetCurrentLineNumber64(parser)
        col = interp_pyexpat.XML_GetCurrentColumnNumber64(parser)
        idx = interp_pyexpat.XML_GetCurrentByteIndex64(parser)
        interp_pyexpat.XML_ParserFree(parser)
        res = interp_pyexpat.XML_ErrorString(3)
        os.write(1, rffi.constcharp2str(res))
        os.write(1, " %d %d %d" % (intmask(line), intmask(col), intmask(idx)))
        return 0

    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()

    builder = CStandaloneBuilder(t, entry_point, t.config)
    builder.generate_source()
    builder.compile()
    data = builder.cmdexec()
    assert data == pyexpat.ErrorString(3) + " 3 2 13", repr(data)
