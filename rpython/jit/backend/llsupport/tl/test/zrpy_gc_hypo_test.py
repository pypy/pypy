from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.history import JitCellToken, NoStats
from rpython.jit.metainterp.history import BasicFinalDescr, BasicFailDescr
from rpython.jit.metainterp.gc import get_description
from rpython.jit.metainterp.optimize import SpeculativeError
from rpython.annotator.listdef import s_list_of_strings
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.rclass import getclassrepr, getinstancerepr
from rpython.translator.unsimplify import call_initial_function
from rpython.translator.translator import TranslationContext
from rpython.translator.c import genc
from rpython.jit.backend.llsupport.tl import interp

class GCHypothesis(object):
    def setup_class(self):
        t = TranslationContext()
        t.config.translation.gc = "incminimark"
        t.config.translation.gcremovetypeptr = True
        ann = t.buildannotator()
        ann.build_types(interp.entry_point, [s_list_of_strings], main_entry_point=True)
        rtyper = t.buildrtyper()
        rtyper.specialize()

        cbuilder = genc.CStandaloneBuilder(t, f, t.config)
        cbuilder.generate_source(defines=cbuilder.DEBUG_DEFINES)
        cbuilder.compile()

        import pdb; pdb.set_trace()


    def test_void(self):
        pass
