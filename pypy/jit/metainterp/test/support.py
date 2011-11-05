
import py, sys
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.jit.backend.llgraph import runner
from pypy.jit.metainterp.warmspot import ll_meta_interp, get_stats
from pypy.jit.metainterp.optimizeopt import ALL_OPTS_DICT
from pypy.jit.metainterp import pyjitpl, history
from pypy.jit.metainterp.warmstate import set_future_value
from pypy.jit.codewriter.policy import JitPolicy
from pypy.jit.codewriter import codewriter, longlong
from pypy.rlib.rfloat import isnan

def _get_jitcodes(testself, CPUClass, func, values, type_system,
                  supports_longlong=False, translationoptions={}, **kwds):
    from pypy.jit.codewriter import support

    class FakeJitCell(object):
        __compiled_merge_points = []
        def get_compiled_merge_points(self):
            return self.__compiled_merge_points[:]
        def set_compiled_merge_points(self, lst):
            self.__compiled_merge_points = lst

    class FakeWarmRunnerState(object):
        def attach_unoptimized_bridge_from_interp(self, greenkey, newloop):
            pass

        def helper_func(self, FUNCPTR, func):
            from pypy.rpython.annlowlevel import llhelper
            return llhelper(FUNCPTR, func)

        def get_location_str(self, args):
            return 'location'

        def jit_cell_at_key(self, greenkey):
            assert greenkey == []
            return self._cell
        _cell = FakeJitCell()

        trace_limit = sys.maxint
        enable_opts = ALL_OPTS_DICT

    func._jit_unroll_safe_ = True
    rtyper = support.annotate(func, values, type_system=type_system,
                              translationoptions=translationoptions)
    graphs = rtyper.annotator.translator.graphs
    testself.all_graphs = graphs
    result_kind = history.getkind(graphs[0].getreturnvar().concretetype)[0]

    class FakeJitDriverSD:
        num_green_args = 0
        portal_graph = graphs[0]
        virtualizable_info = None
        greenfield_info = None
        result_type = result_kind
        portal_runner_ptr = "???"
        on_compile = lambda *args: None
        on_compile_bridge = lambda *args: None

    stats = history.Stats()
    cpu = CPUClass(rtyper, stats, None, False)
    cw = codewriter.CodeWriter(cpu, [FakeJitDriverSD()])
    cw.debug = True
    testself.cw = cw
    policy = JitPolicy()
    policy.set_supports_floats(True)
    policy.set_supports_longlong(supports_longlong)
    cw.find_all_graphs(policy)
    #
    testself.warmrunnerstate = FakeWarmRunnerState()
    testself.warmrunnerstate.cpu = cpu
    FakeJitDriverSD.warmstate = testself.warmrunnerstate
    if hasattr(testself, 'finish_setup_for_interp_operations'):
        testself.finish_setup_for_interp_operations()
    #
    cw.make_jitcodes(verbose=True)

def _run_with_blackhole(testself, args):
    from pypy.jit.metainterp.blackhole import BlackholeInterpBuilder
    cw = testself.cw
    blackholeinterpbuilder = BlackholeInterpBuilder(cw)
    blackholeinterp = blackholeinterpbuilder.acquire_interp()
    count_i = count_r = count_f = 0
    for value in args:
        T = lltype.typeOf(value)
        if T == lltype.Signed:
            blackholeinterp.setarg_i(count_i, value)
            count_i += 1
        elif T == llmemory.GCREF:
            blackholeinterp.setarg_r(count_r, value)
            count_r += 1
        elif T == lltype.Float:
            value = longlong.getfloatstorage(value)
            blackholeinterp.setarg_f(count_f, value)
            count_f += 1
        else:
            raise TypeError(T)
    [jitdriver_sd] = cw.callcontrol.jitdrivers_sd
    blackholeinterp.setposition(jitdriver_sd.mainjitcode, 0)
    blackholeinterp.run()
    return blackholeinterp._final_result_anytype()

def _run_with_pyjitpl(testself, args):

    class DoneWithThisFrame(Exception):
        pass

    class DoneWithThisFrameRef(DoneWithThisFrame):
        def __init__(self, cpu, *args):
            DoneWithThisFrame.__init__(self, *args)

    cw = testself.cw
    opt = history.Options(listops=True)
    metainterp_sd = pyjitpl.MetaInterpStaticData(cw.cpu, opt)
    metainterp_sd.finish_setup(cw)
    [jitdriver_sd] = metainterp_sd.jitdrivers_sd
    metainterp = pyjitpl.MetaInterp(metainterp_sd, jitdriver_sd)
    metainterp_sd.DoneWithThisFrameInt = DoneWithThisFrame
    metainterp_sd.DoneWithThisFrameRef = DoneWithThisFrameRef
    metainterp_sd.DoneWithThisFrameFloat = DoneWithThisFrame
    testself.metainterp = metainterp
    try:
        metainterp.compile_and_run_once(jitdriver_sd, *args)
    except DoneWithThisFrame, e:
        #if conftest.option.view:
        #    metainterp.stats.view()
        return e.args[0]
    else:
        raise Exception("FAILED")

def _run_with_machine_code(testself, args):
    metainterp = testself.metainterp
    num_green_args = metainterp.jitdriver_sd.num_green_args
    loop_tokens = metainterp.get_compiled_merge_points(args[:num_green_args])
    if len(loop_tokens) != 1:
        return NotImplemented
    # a loop was successfully created by _run_with_pyjitpl(); call it
    cpu = metainterp.cpu
    for i in range(len(args) - num_green_args):
        x = args[num_green_args + i]
        typecode = history.getkind(lltype.typeOf(x))
        set_future_value(cpu, i, x, typecode)
    faildescr = cpu.execute_token(loop_tokens[0])
    assert faildescr.__class__.__name__.startswith('DoneWithThisFrameDescr')
    if metainterp.jitdriver_sd.result_type == history.INT:
        return cpu.get_latest_value_int(0)
    elif metainterp.jitdriver_sd.result_type == history.REF:
        return cpu.get_latest_value_ref(0)
    elif metainterp.jitdriver_sd.result_type == history.FLOAT:
        return cpu.get_latest_value_float(0)
    else:
        return None


class JitMixin:
    basic = True
    def check_resops(self, expected=None, **check):
        get_stats().check_resops(expected=expected, **check)

    
    def check_loops(self, expected=None, everywhere=False, **check):
        get_stats().check_loops(expected=expected, everywhere=everywhere,
                                **check)        
    def check_loop_count(self, count):
        """NB. This is a hack; use check_tree_loop_count() or
        check_enter_count() for the real thing.
        This counts as 1 every bridge in addition to every loop; and it does
        not count at all the entry bridges from interpreter, although they
        are TreeLoops as well."""
        assert get_stats().compiled_count == count
    def check_tree_loop_count(self, count):
        assert len(get_stats().loops) == count
    def check_loop_count_at_most(self, count):
        assert get_stats().compiled_count <= count
    def check_enter_count(self, count):
        assert get_stats().enter_count == count
    def check_enter_count_at_most(self, count):
        assert get_stats().enter_count <= count
    def check_jumps(self, maxcount):
        assert get_stats().exec_jumps <= maxcount
    def check_aborted_count(self, count):
        assert get_stats().aborted_count == count
    def check_aborted_count_at_least(self, count):
        assert get_stats().aborted_count >= count

    def meta_interp(self, *args, **kwds):
        kwds['CPUClass'] = self.CPUClass
        kwds['type_system'] = self.type_system
        if "backendopt" not in kwds:
            kwds["backendopt"] = False
        old = codewriter.CodeWriter.debug
        try:
            codewriter.CodeWriter.debug = True
            return ll_meta_interp(*args, **kwds)
        finally:
            codewriter.CodeWriter.debug = old

    def interp_operations(self, f, args, **kwds):
        # get the JitCodes for the function f
        _get_jitcodes(self, self.CPUClass, f, args, self.type_system, **kwds)
        # try to run it with blackhole.py
        result1 = _run_with_blackhole(self, args)
        # try to run it with pyjitpl.py
        result2 = _run_with_pyjitpl(self, args)
        assert result1 == result2 or isnan(result1) and isnan(result2)
        # try to run it by running the code compiled just before
        result3 = _run_with_machine_code(self, args)
        assert result1 == result3 or result3 == NotImplemented or isnan(result1) and isnan(result3)
        #
        if (longlong.supports_longlong and
            isinstance(result1, longlong.r_float_storage)):
            result1 = longlong.getrealfloat(result1)
        return result1

    def check_history(self, expected=None, **isns):
        # this can be used after calling meta_interp
        get_stats().check_history(expected, **isns)

    def check_operations_history(self, expected=None, **isns):
        # this can be used after interp_operations
        if expected is not None:
            expected = dict(expected)
            expected['jump'] = 1
        self.metainterp.staticdata.stats.check_history(expected, **isns)


class LLJitMixin(JitMixin):
    type_system = 'lltype'
    CPUClass = runner.LLtypeCPU

    @staticmethod
    def Ptr(T):
        return lltype.Ptr(T)

    @staticmethod
    def GcStruct(name, *fields, **kwds):
        S = lltype.GcStruct(name, *fields, **kwds)
        return S

    malloc = staticmethod(lltype.malloc)
    nullptr = staticmethod(lltype.nullptr)

    @staticmethod
    def malloc_immortal(T):
        return lltype.malloc(T, immortal=True)

    def _get_NODE(self):
        NODE = lltype.GcForwardReference()
        NODE.become(lltype.GcStruct('NODE', ('value', lltype.Signed),
                                            ('next', lltype.Ptr(NODE))))
        return NODE
    
class OOJitMixin(JitMixin):
    type_system = 'ootype'
    #CPUClass = runner.OOtypeCPU

    def setup_class(cls):
        py.test.skip("ootype tests skipped for now")

    @staticmethod
    def Ptr(T):
        return T

    @staticmethod
    def GcStruct(name, *fields, **kwds):
        if 'hints' in kwds:
            kwds['_hints'] = kwds['hints']
            del kwds['hints']
        I = ootype.Instance(name, ootype.ROOT, dict(fields), **kwds)
        return I

    malloc = staticmethod(ootype.new)
    nullptr = staticmethod(ootype.null)

    @staticmethod
    def malloc_immortal(T):
        return ootype.new(T)

    def _get_NODE(self):
        NODE = ootype.Instance('NODE', ootype.ROOT, {})
        NODE._add_fields({'value': ootype.Signed,
                          'next': NODE})
        return NODE

# ____________________________________________________________

class _Foo:
    pass

def noConst(x):
    """Helper function for tests, returning 'x' as a BoxInt/BoxPtr
    even if it is a ConstInt/ConstPtr."""
    f1 = _Foo(); f2 = _Foo()
    f1.x = x; f2.x = 0
    return f1.x
