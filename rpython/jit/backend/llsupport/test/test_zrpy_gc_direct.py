from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.history import JitCellToken, NoStats
from rpython.jit.metainterp.history import BasicFinalDescr, BasicFailDescr
from rpython.jit.metainterp.gc import get_description
from rpython.annotator.listdef import s_list_of_strings
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.rclass import getclassrepr
from rpython.translator.unsimplify import call_initial_function
from rpython.translator.translator import TranslationContext
from rpython.translator.c import genc


def test_guard_class():
    class A(object):
        pass
    class B(A):
        pass
    class C(B):
        pass
    def main(argv):
        A(); B(); C()
        return 0

    t = TranslationContext()
    t.config.translation.gc = "minimark"
    t.config.translation.gcremovetypeptr = True
    ann = t.buildannotator()
    ann.build_types(main, [s_list_of_strings], main_entry_point=True)
    rtyper = t.buildrtyper()
    rtyper.specialize()

    classdef = ann.bookkeeper.getuniqueclassdef(B)
    rclass = getclassrepr(rtyper, classdef)
    vtable_B = rclass.getvtable()
    adr_vtable_B = llmemory.cast_ptr_to_adr(vtable_B)
    vtable_B = llmemory.cast_adr_to_int(adr_vtable_B, mode="symbolic")

    CPU = getcpuclass()
    cpu = CPU(rtyper, NoStats(),
              translate_support_code=True,
              gcdescr=get_description(t.config))
    execute_token = cpu.make_execute_token(llmemory.GCREF)
    finaldescr = BasicFinalDescr()
    faildescr = BasicFailDescr()

    loop = parse("""
    [p0]
    guard_class(p0, ConstInt(vtable_B), descr=faildescr) []
    finish(descr=finaldescr)
    """, namespace={'finaldescr': finaldescr,
                    'faildescr': faildescr,
                    'vtable_B': vtable_B})

    def g():
        cpu.setup_once()
        token = JitCellToken()
        cpu.compile_loop(loop.inputargs, loop.operations, token)

        for x in [A(),B(), C()]:
            p0 = rffi.cast(llmemory.GCREF, x)
            frame = execute_token(token, p0)
            descr = cpu.get_latest_descr(frame)
            if descr is finaldescr:
                print 'match'
            elif descr is faildescr:
                print 'fail'
            else:
                print '???'

    call_initial_function(t, g)

    cbuilder = genc.CStandaloneBuilder(t, main, t.config)
    cbuilder.generate_source(defines=cbuilder.DEBUG_DEFINES)
    cbuilder.compile()
    
    data = cbuilder.cmdexec('')
    assert data == 'fail\nmatch\nfail\n'
