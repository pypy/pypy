import py
from pypy.jit.codewriter.codewriter import CodeWriter
from pypy.jit.codewriter import support
from pypy.jit.metainterp.history import AbstractDescr
from pypy.rpython.lltypesystem import lltype, llmemory, rffi

class FakeCallDescr(AbstractDescr):
    def __init__(self, FUNC, ARGS, RESULT, effectinfo):
        self.FUNC = FUNC
        self.ARGS = ARGS
        self.RESULT = RESULT
        self.effectinfo = effectinfo
    def get_extra_info(self):
        return self.effectinfo

class FakeFieldDescr(AbstractDescr):
    def __init__(self, STRUCT, fieldname):
        self.STRUCT = STRUCT
        self.fieldname = fieldname

class FakeSizeDescr(AbstractDescr):
    def __init__(self, STRUCT):
        self.STRUCT = STRUCT
    def as_vtable_size_descr(self):
        return self

class FakeArrayDescr(AbstractDescr):
    def __init__(self, ARRAY):
        self.ARRAY = ARRAY

class FakeCPU:
    def __init__(self, rtyper):
        self.rtyper = rtyper
    calldescrof = FakeCallDescr
    fielddescrof = FakeFieldDescr
    sizeof = FakeSizeDescr
    arraydescrof = FakeArrayDescr

class FakePolicy:
    def look_inside_graph(self, graph):
        return graph.name != 'dont_look'

class FakeJitDriverSD:
    def __init__(self, portal_graph):
        self.portal_graph = portal_graph
        self.portal_runner_ptr = "???"
        self.virtualizable_info = None
        self.greenfield_info = None


def test_loop():
    def f(a, b):
        while a > 0:
            b += a
            a -= 1
        return b
    cw = CodeWriter()
    jitcode = cw.transform_func_to_jitcode(f, [5, 6])
    assert jitcode.code == ("\x00\x00\x00\x10\x00"   # ends at 5
                            "\x01\x01\x00\x01"
                            "\x02\x00\x01\x00"
                            "\x03\x00\x00"
                            "\x04\x01")
    assert cw.assembler.insns == {'goto_if_not_int_gt/icL': 0,
                                  'int_add/ii>i': 1,
                                  'int_sub/ic>i': 2,
                                  'goto/L': 3,
                                  'int_return/i': 4}
    assert jitcode.num_regs_i() == 2
    assert jitcode.num_regs_r() == 0
    assert jitcode.num_regs_f() == 0
    assert jitcode._live_vars(5) == '%i0 %i1'
    #
    from pypy.jit.codewriter.jitcode import MissingLiveness
    for i in range(len(jitcode.code)+1):
        if i != 5:
            py.test.raises(MissingLiveness, jitcode._live_vars, i)

def test_call():
    def ggg(x):
        return x * 2
    def fff(a, b):
        return ggg(b) - ggg(a)
    rtyper = support.annotate(fff, [35, 42])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cw = CodeWriter(FakeCPU(rtyper), [jitdriver_sd])
    cw.find_all_graphs(FakePolicy())
    cw.make_jitcodes(verbose=True)
    jitcode = jitdriver_sd.mainjitcode
    print jitcode.dump()
    [jitcode2] = cw.assembler.descrs
    print jitcode2.dump()
    assert jitcode is not jitcode2
    assert jitcode.name == 'fff'
    assert jitcode2.name == 'ggg'
    assert 'ggg' in jitcode.dump()
    assert lltype.typeOf(jitcode2.fnaddr) == llmemory.Address
    assert isinstance(jitcode2.calldescr, FakeCallDescr)

def test_integration():
    from pypy.jit.metainterp.blackhole import BlackholeInterpBuilder
    def f(a, b):
        while a > 2:
            b += a
            a -= 1
        return b
    cw = CodeWriter()
    jitcode = cw.transform_func_to_jitcode(f, [5, 6])
    blackholeinterpbuilder = BlackholeInterpBuilder(cw)
    blackholeinterp = blackholeinterpbuilder.acquire_interp()
    blackholeinterp.setposition(jitcode, 0)
    blackholeinterp.setarg_i(0, 6)
    blackholeinterp.setarg_i(1, 100)
    blackholeinterp.run()
    assert blackholeinterp.get_tmpreg_i() == 100+6+5+4+3

def test_instantiate():
    class A1:     id = 651
    class A2(A1): id = 652
    class B1:     id = 661
    class B2(B1): id = 662
    def dont_look(n):
        return n + 1
    def f(n):
        if n > 5:
            x, y = A1, B1
        else:
            x, y = A2, B2
        return x().id + y().id + dont_look(n)
    rtyper = support.annotate(f, [35])
    maingraph = rtyper.annotator.translator.graphs[0]
    cw = CodeWriter(FakeCPU(rtyper), [FakeJitDriverSD(maingraph)])
    cw.find_all_graphs(FakePolicy())
    cw.make_jitcodes(verbose=True)
    #
    assert len(cw.assembler.indirectcalltargets) == 4
    names = [jitcode.name for jitcode in cw.assembler.indirectcalltargets]
    for expected in ['A1', 'A2', 'B1', 'B2']:
        for name in names:
            if name.startswith('instantiate_') and name.endswith(expected):
                break
        else:
            assert 0, "missing instantiate_*_%s in:\n%r" % (expected,
                                                            names)
    #
    print cw.assembler.list_of_addr2name
    names = dict.fromkeys([value
                           for key, value in cw.assembler.list_of_addr2name])
    assert 'A1' in names
    assert 'B1' in names
    assert 'A2' in names
    assert 'B2' in names
    assert 'dont_look' in names

def test_instantiate_with_unreasonable_attr():
    # It is possible to have in real code the instantiate() function for
    # a class be dont-look-inside.  This is caused by the code that
    # initialize the instance attributes: if one attribute has a strange
    # type, the whole function is disabled.  Check that it still works.
    class MyFakePolicy:
        def look_inside_graph(self, graph):
            name = graph.name
            return not (name.startswith('instantiate_') and
                        name.endswith('A2'))
    class A1:
        pass
    class A2(A1):
        pass
    def f(n):
        if n > 5:
            x = A1
        else:
            x = A2
        x()
    rtyper = support.annotate(f, [35])
    maingraph = rtyper.annotator.translator.graphs[0]
    cw = CodeWriter(FakeCPU(rtyper), [FakeJitDriverSD(maingraph)])
    cw.find_all_graphs(MyFakePolicy())
    cw.make_jitcodes(verbose=True)
    #
    names = [jitcode.name for jitcode in cw.assembler.indirectcalltargets]
    assert len(names) == 1
    assert names[0].startswith('instantiate_') and names[0].endswith('A1')
    #
    print cw.assembler.list_of_addr2name
    names = dict.fromkeys([value
                           for key, value in cw.assembler.list_of_addr2name])
    assert 'A1' in names
    assert 'A2' in names

def test_int_abs():
    def f(n):
        return abs(n)
    rtyper = support.annotate(f, [35])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cw = CodeWriter(FakeCPU(rtyper), [jitdriver_sd])
    cw.find_all_graphs(FakePolicy())
    cw.make_jitcodes(verbose=True)
    #
    s = jitdriver_sd.mainjitcode.dump()
    assert "inline_call_ir_i <JitCode '_ll_1_int_abs__Signed'>" in s

def test_raw_malloc_and_access():
    TP = rffi.CArray(lltype.Signed)
    
    def f(n):
        a = lltype.malloc(TP, n, flavor='raw')
        a[0] = n
        res = a[0]
        lltype.free(a, flavor='raw')
        return res

    rtyper = support.annotate(f, [35])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cw = CodeWriter(FakeCPU(rtyper), [jitdriver_sd])
    cw.find_all_graphs(FakePolicy())
    cw.make_jitcodes(verbose=True)
    #
    s = jitdriver_sd.mainjitcode.dump()
    assert 'residual_call_ir_i $<* fn _ll_1_raw_malloc__Signed>' in s
    assert 'setarrayitem_raw_i' in s
    assert 'getarrayitem_raw_i' in s
    assert 'residual_call_ir_v $<* fn _ll_1_raw_free__arrayPtr>' in s
