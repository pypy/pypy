import py

from rpython.flowspace.model import SpaceOperation, Constant, Variable
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.unsimplify import varoftype
from rpython.rlib import jit
from rpython.jit.codewriter import support, call
from rpython.jit.codewriter.call import CallControl
from rpython.jit.codewriter.effectinfo import EffectInfo, CallShortcut


class FakePolicy:
    def look_inside_graph(self, graph):
        return True


def test_graphs_from_direct_call():
    cc = CallControl()
    F = lltype.FuncType([], lltype.Signed)
    f = lltype.functionptr(F, 'f', graph='fgraph')
    v = varoftype(lltype.Signed)
    op = SpaceOperation('direct_call', [Constant(f, lltype.Ptr(F))], v)
    #
    lst = cc.graphs_from(op, {}.__contains__)
    assert lst is None     # residual call
    #
    lst = cc.graphs_from(op, {'fgraph': True}.__contains__)
    assert lst == ['fgraph']     # normal call

def test_graphs_from_indirect_call():
    cc = CallControl()
    F = lltype.FuncType([], lltype.Signed)
    v = varoftype(lltype.Signed)
    graphlst = ['f1graph', 'f2graph']
    op = SpaceOperation('indirect_call', [varoftype(lltype.Ptr(F)),
                                          Constant(graphlst, lltype.Void)], v)
    #
    lst = cc.graphs_from(op, {'f1graph': True, 'f2graph': True}.__contains__)
    assert lst == ['f1graph', 'f2graph']     # normal indirect call
    #
    lst = cc.graphs_from(op, {'f1graph': True}.__contains__)
    assert lst == ['f1graph']     # indirect call, look only inside some graphs
    #
    lst = cc.graphs_from(op, {}.__contains__)
    assert lst is None            # indirect call, don't look inside any graph

def test_graphs_from_no_target():
    cc = CallControl()
    F = lltype.FuncType([], lltype.Signed)
    v = varoftype(lltype.Signed)
    op = SpaceOperation('indirect_call', [varoftype(lltype.Ptr(F)),
                                          Constant(None, lltype.Void)], v)
    lst = cc.graphs_from(op, {}.__contains__)
    assert lst is None

# ____________________________________________________________

class FakeJitDriverSD:
    def __init__(self, portal_graph):
        self.portal_graph = portal_graph
        self.portal_runner_ptr = "???"

def test_find_all_graphs():
    def g(x):
        return x + 2
    def f(x):
        return g(x) + 1
    rtyper = support.annotate(f, [7])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())
    funcs = set([graph.func for graph in res])
    assert funcs == set([f, g])

def test_find_all_graphs_without_g():
    def g(x):
        return x + 2
    def f(x):
        return g(x) + 1
    rtyper = support.annotate(f, [7])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(jitdrivers_sd=[jitdriver_sd])
    class CustomFakePolicy:
        def look_inside_graph(self, graph):
            assert graph.name == 'g'
            return False
    res = cc.find_all_graphs(CustomFakePolicy())
    funcs = [graph.func for graph in res]
    assert funcs == [f]

# ____________________________________________________________

def test_guess_call_kind_and_calls_from_graphs():
    class portal_runner_obj:
        graph = object()
    class FakeJitDriverSD:
        portal_runner_ptr = portal_runner_obj
    g = object()
    g1 = object()
    cc = CallControl(jitdrivers_sd=[FakeJitDriverSD()])
    cc.candidate_graphs = [g, g1]

    op = SpaceOperation('direct_call', [Constant(portal_runner_obj)],
                        Variable())
    assert cc.guess_call_kind(op) == 'recursive'

    class fakeresidual:
        _obj = object()
    op = SpaceOperation('direct_call', [Constant(fakeresidual)],
                        Variable())
    assert cc.guess_call_kind(op) == 'residual'

    class funcptr:
        class _obj:
            class graph:
                class func:
                    oopspec = "spec"
    op = SpaceOperation('direct_call', [Constant(funcptr)],
                        Variable())
    assert cc.guess_call_kind(op) == 'builtin'

    class funcptr:
        class _obj:
            graph = g
    op = SpaceOperation('direct_call', [Constant(funcptr)],
                        Variable())
    res = cc.graphs_from(op)
    assert res == [g]
    assert cc.guess_call_kind(op) == 'regular'

    class funcptr:
        class _obj:
            graph = object()
    op = SpaceOperation('direct_call', [Constant(funcptr)],
                        Variable())
    res = cc.graphs_from(op)
    assert res is None
    assert cc.guess_call_kind(op) == 'residual'

    h = object()
    op = SpaceOperation('indirect_call', [Variable(),
                                          Constant([g, g1, h])],
                        Variable())
    res = cc.graphs_from(op)
    assert res == [g, g1]
    assert cc.guess_call_kind(op) == 'regular'

    op = SpaceOperation('indirect_call', [Variable(),
                                          Constant([h])],
                        Variable())
    res = cc.graphs_from(op)
    assert res is None
    assert cc.guess_call_kind(op) == 'residual'

# ____________________________________________________________

def test_get_jitcode(monkeypatch):
    from rpython.jit.codewriter.test.test_flatten import FakeCPU
    class FakeRTyper:
        class annotator:
            translator = None

    def getfunctionptr(graph):
        F = lltype.FuncType([], lltype.Signed)
        return lltype.functionptr(F, 'bar')

    monkeypatch.setattr(call, 'getfunctionptr', getfunctionptr)
    cc = CallControl(FakeCPU(FakeRTyper()))
    class somegraph:
        name = "foo"
    jitcode = cc.get_jitcode(somegraph)
    assert jitcode is cc.get_jitcode(somegraph)    # caching
    assert jitcode.name == "foo"
    pending = list(cc.enum_pending_graphs())
    assert pending == [(somegraph, jitcode)]

# ____________________________________________________________

def test_jit_force_virtualizable_effectinfo():
    py.test.skip("XXX add a test for CallControl.getcalldescr() -> EF_xxx")

def test_releases_gil_analyzer():
    from rpython.jit.backend.llgraph.runner import LLGraphCPU

    T = rffi.CArrayPtr(rffi.TIME_T)
    external = rffi.llexternal("time", [T], rffi.TIME_T, releasegil=True)

    @jit.dont_look_inside
    def f():
        return external(lltype.nullptr(T.TO))

    rtyper = support.annotate(f, [])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(LLGraphCPU(rtyper), jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())

    [f_graph] = [x for x in res if x.func is f]
    [block, _] = list(f_graph.iterblocks())
    [op] = block.operations
    call_descr = cc.getcalldescr(op)
    assert call_descr.extrainfo.has_random_effects()
    assert call_descr.extrainfo.is_call_release_gil() is False

def test_call_release_gil():
    from rpython.jit.backend.llgraph.runner import LLGraphCPU

    T = rffi.CArrayPtr(rffi.TIME_T)
    external = rffi.llexternal("time", [T], rffi.TIME_T, releasegil=True,
                               save_err=rffi.RFFI_SAVE_ERRNO)

    # no jit.dont_look_inside in this test
    def f():
        return external(lltype.nullptr(T.TO))

    rtyper = support.annotate(f, [])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(LLGraphCPU(rtyper), jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())

    [llext_graph] = [x for x in res if x.func is external]
    [block, _] = list(llext_graph.iterblocks())
    [op] = block.operations
    tgt_tuple = op.args[0].value._obj.graph.func._call_aroundstate_target_
    assert type(tgt_tuple) is tuple and len(tgt_tuple) == 2
    call_target, saveerr = tgt_tuple
    assert saveerr == rffi.RFFI_SAVE_ERRNO
    call_target = llmemory.cast_ptr_to_adr(call_target)
    call_descr = cc.getcalldescr(op)
    assert call_descr.extrainfo.has_random_effects()
    assert call_descr.extrainfo.is_call_release_gil() is True
    assert call_descr.extrainfo.call_release_gil_target == (
        call_target, rffi.RFFI_SAVE_ERRNO)

def test_random_effects_on_stacklet_switch():
    from rpython.jit.backend.llgraph.runner import LLGraphCPU
    from rpython.translator.platform import CompilationError
    try:
        from rpython.rlib._rffi_stacklet import switch, handle
    except CompilationError as e:
        if "Unsupported platform!" in e.out:
            py.test.skip("Unsupported platform!")
        else:
            raise e
    @jit.dont_look_inside
    def f():
        switch(rffi.cast(handle, 0))

    rtyper = support.annotate(f, [])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(LLGraphCPU(rtyper), jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())

    [f_graph] = [x for x in res if x.func is f]
    [block, _] = list(f_graph.iterblocks())
    op = block.operations[-1]
    call_descr = cc.getcalldescr(op)
    assert call_descr.extrainfo.has_random_effects()

def test_no_random_effects_for_rotateLeft():
    from rpython.jit.backend.llgraph.runner import LLGraphCPU
    from rpython.rlib.rarithmetic import r_uint

    if r_uint.BITS == 32:
        py.test.skip("64-bit only")

    from rpython.rlib.rmd5 import _rotateLeft
    def f(n, m):
        return _rotateLeft(r_uint(n), m)

    rtyper = support.annotate(f, [7, 9])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(LLGraphCPU(rtyper), jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())

    [f_graph] = [x for x in res if x.func is f]
    [block, _] = list(f_graph.iterblocks())
    op = block.operations[-1]
    call_descr = cc.getcalldescr(op)
    assert not call_descr.extrainfo.has_random_effects()
    assert call_descr.extrainfo.check_is_elidable()

def test_elidable_kinds():
    from rpython.jit.backend.llgraph.runner import LLGraphCPU

    @jit.elidable
    def f1(n, m):
        return n + m
    @jit.elidable
    def f2(n, m):
        return [n, m]    # may raise MemoryError
    @jit.elidable
    def f3(n, m):
        if n > m:
            raise ValueError
        return n + m

    def f(n, m):
        a = f1(n, m)
        b = f2(n, m)
        c = f3(n, m)
        return a + len(b) + c

    rtyper = support.annotate(f, [7, 9])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(LLGraphCPU(rtyper), jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())
    [f_graph] = [x for x in res if x.func is f]

    for index, expected in [
            (0, EffectInfo.EF_ELIDABLE_CANNOT_RAISE),
            (1, EffectInfo.EF_ELIDABLE_OR_MEMORYERROR),
            (2, EffectInfo.EF_ELIDABLE_CAN_RAISE)]:
        call_op = f_graph.startblock.operations[index]
        assert call_op.opname == 'direct_call'
        call_descr = cc.getcalldescr(call_op)
        assert call_descr.extrainfo.extraeffect == expected

def test_raise_elidable_no_result():
    from rpython.jit.backend.llgraph.runner import LLGraphCPU
    l = []
    @jit.elidable
    def f1(n, m):
        l.append(n)
    def f(n, m):
        f1(n, m)
        return n + m

    rtyper = support.annotate(f, [7, 9])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(LLGraphCPU(rtyper), jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())
    [f_graph] = [x for x in res if x.func is f]
    call_op = f_graph.startblock.operations[0]
    assert call_op.opname == 'direct_call'
    with py.test.raises(Exception):
        call_descr = cc.getcalldescr(call_op)

def test_can_or_cannot_collect():
    from rpython.jit.backend.llgraph.runner import LLGraphCPU
    prebuilts = [[5], [6]]
    l = []
    def f1(n):
        if n > 1:
            raise IndexError
        return prebuilts[n]    # cannot collect
    f1._dont_inline_ = True

    def f2(n):
        return [n]         # can collect
    f2._dont_inline_ = True

    def f(n):
        a = f1(n)
        b = f2(n)
        return len(a) + len(b)

    rtyper = support.annotate(f, [1])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(LLGraphCPU(rtyper), jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())
    [f_graph] = [x for x in res if x.func is f]
    for index, expected in [
            (0, False),    # f1()
            (1, True),     # f2()
            (2, False),    # len()
            (3, False)]:   # len()
        call_op = f_graph.startblock.operations[index]
        assert call_op.opname == 'direct_call'
        call_descr = cc.getcalldescr(call_op)
        assert call_descr.extrainfo.check_can_collect() == expected

def test_find_call_shortcut():
    class FakeCPU:
        def fielddescrof(self, TYPE, fieldname):
            if isinstance(TYPE, lltype.GcStruct):
                if fieldname == 'inst_foobar':
                    return 'foobardescr'
                if fieldname == 'inst_fooref':
                    return 'foorefdescr'
            if TYPE == RAW and fieldname == 'x':
                return 'xdescr'
            assert False, (TYPE, fieldname)
    cc = CallControl(FakeCPU())

    class B(object):
        foobar = 0
        fooref = None

    def f1(a, b, c):
        if b.foobar:
            return b.foobar
        b.foobar = a + c
        return b.foobar

    def f2(x, y, z, b):
        r = b.fooref
        if r is not None:
            return r
        r = b.fooref = B()
        return r

    class Space(object):
        def _freeze_(self):
            return True
    space = Space()

    def f3(space, b):
        r = b.foobar
        if not r:
            r = b.foobar = 123
        return r

    def f4(raw):
        r = raw.x
        if r != 0:
            return r
        raw.x = 123
        return 123
    RAW = lltype.Struct('RAW', ('x', lltype.Signed))

    def f(a, c):
        b = B()
        f1(a, b, c)
        f2(a, c, a, b)
        f3(space, b)
        r = lltype.malloc(RAW, flavor='raw')
        f4(r)

    rtyper = support.annotate(f, [10, 20])
    f1_graph = rtyper.annotator.translator._graphof(f1)
    assert cc.find_call_shortcut(f1_graph) == CallShortcut(1, "foobardescr")
    f2_graph = rtyper.annotator.translator._graphof(f2)
    assert cc.find_call_shortcut(f2_graph) == CallShortcut(3, "foorefdescr")
    f3_graph = rtyper.annotator.translator._graphof(f3)
    assert cc.find_call_shortcut(f3_graph) == CallShortcut(0, "foobardescr")
    f4_graph = rtyper.annotator.translator._graphof(f4)
    assert cc.find_call_shortcut(f4_graph) == CallShortcut(0, "xdescr")

def test_cant_find_call_shortcut():
    from rpython.jit.backend.llgraph.runner import LLGraphCPU

    @jit.dont_look_inside
    @jit.call_shortcut
    def f1(n):
        return n + 17   # no call shortcut found

    def f(n):
        return f1(n)

    rtyper = support.annotate(f, [1])
    jitdriver_sd = FakeJitDriverSD(rtyper.annotator.translator.graphs[0])
    cc = CallControl(LLGraphCPU(rtyper), jitdrivers_sd=[jitdriver_sd])
    res = cc.find_all_graphs(FakePolicy())
    [f_graph] = [x for x in res if x.func is f]
    call_op = f_graph.startblock.operations[0]
    assert call_op.opname == 'direct_call'
    e = py.test.raises(AssertionError, cc.getcalldescr, call_op)
    assert "shortcut not found" in str(e.value)
