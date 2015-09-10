from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.tool.oparser import parse
from rpython.jit.metainterp.history import JitCellToken, NoStats
from rpython.jit.metainterp.history import BasicFinalDescr, BasicFailDescr
from rpython.jit.metainterp.gc import get_description
from rpython.annotator.listdef import s_list_of_strings
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.rclass import getclassrepr, getinstancerepr
from rpython.translator.unsimplify import call_initial_function
from rpython.translator.translator import TranslationContext
from rpython.translator.c import genc


def run_guards_translated(gcremovetypeptr):
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
    t.config.translation.gcremovetypeptr = gcremovetypeptr
    ann = t.buildannotator()
    ann.build_types(main, [s_list_of_strings], main_entry_point=True)
    rtyper = t.buildrtyper()
    rtyper.specialize()

    classdef = ann.bookkeeper.getuniqueclassdef(B)
    rclass = getclassrepr(rtyper, classdef)
    rinstance = getinstancerepr(rtyper, classdef)
    LLB = rinstance.lowleveltype.TO
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

    descr_B = cpu.sizeof(LLB, vtable_B)
    typeid_B = descr_B.get_type_id()

    loop1 = parse("""
    [p0]
    guard_class(p0, ConstInt(vtable_B), descr=faildescr) []
    finish(descr=finaldescr)
    """, namespace={'finaldescr': finaldescr,
                    'faildescr': faildescr,
                    'vtable_B': vtable_B})

    loop2 = parse("""
    [p0]
    guard_gc_type(p0, ConstInt(typeid_B), descr=faildescr) []
    finish(descr=finaldescr)
    """, namespace={'finaldescr': finaldescr,
                    'faildescr': faildescr,
                    'typeid_B': typeid_B})

    loop3 = parse("""
    [p0]
    guard_is_object(p0, descr=faildescr) []
    finish(descr=finaldescr)
    """, namespace={'finaldescr': finaldescr,
                    'faildescr': faildescr})

    loop4 = parse("""
    [p0]
    guard_subclass(p0, ConstInt(vtable_B), descr=faildescr) []
    finish(descr=finaldescr)
    """, namespace={'finaldescr': finaldescr,
                    'faildescr': faildescr,
                    'vtable_B': vtable_B})

    def g():
        cpu.setup_once()
        token1 = JitCellToken()
        token2 = JitCellToken()
        token3 = JitCellToken()
        token4 = JitCellToken()
        cpu.compile_loop(loop1.inputargs, loop1.operations, token1)
        cpu.compile_loop(loop2.inputargs, loop2.operations, token2)
        cpu.compile_loop(loop3.inputargs, loop3.operations, token3)
        cpu.compile_loop(loop4.inputargs, loop4.operations, token4)

        for token, p0 in [
                (token1, rffi.cast(llmemory.GCREF, A())),
                (token1, rffi.cast(llmemory.GCREF, B())),
                (token1, rffi.cast(llmemory.GCREF, C())),

                (token2, rffi.cast(llmemory.GCREF, A())),
                (token2, rffi.cast(llmemory.GCREF, B())),
                (token2, rffi.cast(llmemory.GCREF, C())),
                (token2, rffi.cast(llmemory.GCREF, [42, 43])),

                (token3, rffi.cast(llmemory.GCREF, A())),
                (token3, rffi.cast(llmemory.GCREF, B())),
                (token3, rffi.cast(llmemory.GCREF, [44, 45])),

                (token4, rffi.cast(llmemory.GCREF, A())),
                (token4, rffi.cast(llmemory.GCREF, B())),
                (token4, rffi.cast(llmemory.GCREF, C())),
                ]:
            frame = execute_token(token, p0)
            descr = cpu.get_latest_descr(frame)
            if descr is finaldescr:
                print 'match'
            elif descr is faildescr:
                print 'fail'
            else:
                print '???'
            #
            if token is token2:    # guard_gc_type
                print int(cpu.get_actual_typeid(p0) == typeid_B)
            if token is token3:    # guard_is_object
                print int(cpu.check_is_object(p0))

    call_initial_function(t, g)

    cbuilder = genc.CStandaloneBuilder(t, main, t.config)
    cbuilder.generate_source(defines=cbuilder.DEBUG_DEFINES)
    cbuilder.compile()
    
    data = cbuilder.cmdexec('')
    assert data == ('fail\n'
                    'match\n'
                    'fail\n'

                    'fail\n'  '0\n'
                    'match\n' '1\n'
                    'fail\n'  '0\n'
                    'fail\n'  '0\n'

                    'match\n' '1\n'
                    'match\n' '1\n'
                    'fail\n'  '0\n'

                    'fail\n'
                    'match\n'
                    'match\n')


def test_guards_translated_with_gctypeptr():
    run_guards_translated(gcremovetypeptr=False)

def test_guards_translated_without_gctypeptr():
    run_guards_translated(gcremovetypeptr=True)
