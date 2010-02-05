import sys, py
from pypy.rpython.lltypesystem import lltype, llmemory, rclass, rstr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import llhelper, MixLevelHelperAnnotator,\
     cast_base_ptr_to_instance, hlstr
from pypy.annotation import model as annmodel
from pypy.rpython.llinterp import LLException
from pypy.rpython.test.test_llinterp import get_interpreter, clear_tcache
from pypy.objspace.flow.model import SpaceOperation, Variable, Constant
from pypy.objspace.flow.model import checkgraph, Link, copygraph
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.debug import debug_print, fatalerror
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.translator.simplify import get_funcobj, get_functype
from pypy.translator.unsimplify import call_final_function

from pypy.jit.metainterp import codewriter
from pypy.jit.metainterp import support, history, pyjitpl, gc
from pypy.jit.metainterp.pyjitpl import MetaInterpStaticData, MetaInterp
from pypy.jit.metainterp.policy import JitPolicy
from pypy.jit.metainterp.typesystem import LLTypeHelper, OOTypeHelper
from pypy.jit.metainterp.jitprof import Profiler, EmptyProfiler
from pypy.rlib.jit import DEBUG_STEPS, DEBUG_DETAILED, DEBUG_OFF, DEBUG_PROFILE

# ____________________________________________________________
# Bootstrapping

def apply_jit(translator, backend_name="auto", debug_level=DEBUG_STEPS,
              inline=False,
              **kwds):
    if 'CPUClass' not in kwds:
        from pypy.jit.backend.detect_cpu import getcpuclass
        kwds['CPUClass'] = getcpuclass(backend_name)
    if debug_level > DEBUG_OFF:
        ProfilerClass = Profiler
    else:
        ProfilerClass = EmptyProfiler
    warmrunnerdesc = WarmRunnerDesc(translator,
                                    translate_support_code=True,
                                    listops=True,
                                    no_stats = True,
                                    ProfilerClass = ProfilerClass,
                                    **kwds)
    warmrunnerdesc.state.set_param_inlining(inline)
    warmrunnerdesc.state.set_param_debug(debug_level)
    warmrunnerdesc.finish()
    translator.warmrunnerdesc = warmrunnerdesc    # for later debugging

def ll_meta_interp(function, args, backendopt=False, type_system='lltype',
                   listcomp=False, **kwds):
    if listcomp:
        extraconfigopts = {'translation.list_comprehension_operations': True}
    else:
        extraconfigopts = {}
    interp, graph = get_interpreter(function, args,
                                    backendopt=False,  # will be done below
                                    type_system=type_system,
                                    **extraconfigopts)
    clear_tcache()
    return jittify_and_run(interp, graph, args, backendopt=backendopt, **kwds)

def jittify_and_run(interp, graph, args, repeat=1,
                    backendopt=False, trace_limit=sys.maxint,
                    debug_level=DEBUG_STEPS, inline=False, **kwds):
    translator = interp.typer.annotator.translator
    translator.config.translation.gc = "boehm"
    translator.config.translation.list_comprehension_operations = True
    warmrunnerdesc = WarmRunnerDesc(translator, backendopt=backendopt, **kwds)
    warmrunnerdesc.state.set_param_threshold(3)          # for tests
    warmrunnerdesc.state.set_param_trace_eagerness(2)    # for tests
    warmrunnerdesc.state.set_param_trace_limit(trace_limit)
    warmrunnerdesc.state.set_param_inlining(inline)
    warmrunnerdesc.state.set_param_debug(debug_level)
    warmrunnerdesc.finish()
    res = interp.eval_graph(graph, args)
    if not kwds.get('translate_support_code', False):
        warmrunnerdesc.metainterp_sd.profiler.finish()
        warmrunnerdesc.metainterp_sd.cpu.finish_once()
    print '~~~ return value:', res
    while repeat > 1:
        print '~' * 79
        res1 = interp.eval_graph(graph, args)
        if isinstance(res, int):
            assert res1 == res
        repeat -= 1
    return res

def rpython_ll_meta_interp(function, args, backendopt=True,
                           loops='not used right now', **kwds):
    return ll_meta_interp(function, args, backendopt=backendopt,
                          translate_support_code=True, **kwds)

def _find_jit_marker(graphs, marker_name):
    results = []
    for graph in graphs:
        for block in graph.iterblocks():
            for i in range(len(block.operations)):
                op = block.operations[i]
                if (op.opname == 'jit_marker' and
                    op.args[0].value == marker_name):
                    results.append((graph, block, i))
    return results

def find_can_enter_jit(graphs):
    results = _find_jit_marker(graphs, 'can_enter_jit')
    if not results:
        raise Exception("no can_enter_jit found!")
    return results

def find_jit_merge_point(graphs):
    results = _find_jit_marker(graphs, 'jit_merge_point')
    if len(results) != 1:
        raise Exception("found %d jit_merge_points, need exactly one!" %
                        (len(results),))
    return results[0]

def find_set_param(graphs):
    return _find_jit_marker(graphs, 'set_param')

def get_stats():
    return pyjitpl._warmrunnerdesc.stats

def get_translator():
    return pyjitpl._warmrunnerdesc.translator

def debug_checks():
    stats = get_stats()
    stats.maybe_view()
    stats.check_consistency()

class JitException(Exception):
    _go_through_llinterp_uncaught_ = True     # ugh

class ContinueRunningNormallyBase(JitException):
    pass

class CannotInlineCanEnterJit(JitException):
    pass

# ____________________________________________________________

class WarmRunnerDesc(object):

    def __init__(self, translator, policy=None, backendopt=True, CPUClass=None,
                 optimizer=None, **kwds):
        pyjitpl._warmrunnerdesc = self   # this is a global for debugging only!
        if policy is None:
            policy = JitPolicy()
        self.set_translator(translator)
        self.find_portal()
        self.make_leave_jit_graph()
        self.codewriter = codewriter.CodeWriter(self.rtyper)
        graphs = self.codewriter.find_all_graphs(self.portal_graph,
                                                 self.leave_graph,
                                                 policy,
                                                 CPUClass.supports_floats)
        policy.dump_unsafe_loops()
        self.check_access_directly_sanity(graphs)
        if backendopt:
            self.prejit_optimizations(policy, graphs)

        self.build_meta_interp(CPUClass, **kwds)
        self.make_args_specification()
        #
        from pypy.jit.metainterp.virtualref import VirtualRefInfo
        self.metainterp_sd.virtualref_info = VirtualRefInfo(self)
        if self.jitdriver.virtualizables:
            from pypy.jit.metainterp.virtualizable import VirtualizableInfo
            self.metainterp_sd.virtualizable_info = VirtualizableInfo(self)
        #
        self.make_exception_classes()
        self.make_driverhook_graphs()
        self.make_enter_function()
        self.rewrite_jit_merge_point(policy)
                
        self.codewriter.generate_bytecode(self.metainterp_sd,
                                          self.portal_graph,
                                          self.leave_graph,
                                          self.portal_runner_ptr
                                          )
        self.rewrite_can_enter_jit()
        self.rewrite_set_param()
        self.rewrite_force_virtual()
        self.add_finish()
        self.metainterp_sd.finish_setup(optimizer=optimizer)

    def finish(self):
        vinfo = self.metainterp_sd.virtualizable_info
        if vinfo is not None:
            vinfo.finish()
        if self.cpu.translate_support_code:
            self.annhelper.finish()

    def _freeze_(self):
        return True

    def set_translator(self, translator):
        self.translator = translator
        self.rtyper = translator.rtyper
        self.gcdescr = gc.get_description(translator.config)

    def find_portal(self):
        graphs = self.translator.graphs
        self.jit_merge_point_pos = find_jit_merge_point(graphs)
        graph, block, pos = self.jit_merge_point_pos
        op = block.operations[pos]
        args = op.args[2:]
        s_binding = self.translator.annotator.binding
        self.portal_args_s = [s_binding(v) for v in args]
        graph = copygraph(graph)
        graph.startblock.isstartblock = False
        graph.startblock = support.split_before_jit_merge_point(
            *find_jit_merge_point([graph]))
        graph.startblock.isstartblock = True
        # a crash in the following checkgraph() means that you forgot
        # to list some variable in greens=[] or reds=[] in JitDriver.
        checkgraph(graph)
        for v in graph.getargs():
            assert isinstance(v, Variable)
        assert len(dict.fromkeys(graph.getargs())) == len(graph.getargs())
        self.translator.graphs.append(graph)
        self.portal_graph = graph
        # it's a bit unbelievable to have a portal without func
        assert hasattr(graph, "func")
        graph.func._dont_inline_ = True
        graph.func._jit_unroll_safe_ = True
        self.jitdriver = block.operations[pos].args[1].value

    def check_access_directly_sanity(self, graphs):
        from pypy.translator.backendopt.inline import collect_called_graphs
        jit_graphs = set(graphs)
        for graph in collect_called_graphs(self.translator.graphs[0],
                                           self.translator):
            if graph in jit_graphs:
                continue
            assert not getattr(graph, 'access_directly', False)

    def prejit_optimizations(self, policy, graphs):
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(self.translator,
                              graphs=graphs,
                              merge_if_blocks=True,
                              constfold=True,
                              raisingop2direct_call=False,
                              remove_asserts=True,
                              really_remove_asserts=True)

    def build_meta_interp(self, CPUClass, translate_support_code=False,
                          view="auto", no_stats=False,
                          ProfilerClass=EmptyProfiler, **kwds):
        assert CPUClass is not None
        opt = history.Options(**kwds)
        if no_stats:
            stats = history.NoStats()
        else:
            stats = history.Stats()
        self.stats = stats 
        if translate_support_code:
            self.annhelper = MixLevelHelperAnnotator(self.translator.rtyper)
            annhelper = self.annhelper
        else:
            annhelper = None
        cpu = CPUClass(self.translator.rtyper, self.stats, opt,
                       translate_support_code, gcdescr=self.gcdescr)
        self.cpu = cpu
        self.metainterp_sd = MetaInterpStaticData(self.portal_graph, # xxx
                                                  cpu,
                                                  self.stats, opt,
                                                  ProfilerClass=ProfilerClass,
                                                  warmrunnerdesc=self)

    def make_exception_classes(self):
        portalfunc_ARGS = unrolling_iterable(
            [(i, 'arg%d' % i, ARG) for i, ARG in enumerate(self.PORTAL_FUNCTYPE.ARGS)])
        class DoneWithThisFrameVoid(JitException):
            def __str__(self):
                return 'DoneWithThisFrameVoid()'

        class DoneWithThisFrameInt(JitException):
            def __init__(self, result):
                assert lltype.typeOf(result) is lltype.Signed
                self.result = result
            def __str__(self):
                return 'DoneWithThisFrameInt(%s)' % (self.result,)

        class DoneWithThisFrameRef(JitException):
            def __init__(self, cpu, result):
                assert lltype.typeOf(result) == cpu.ts.BASETYPE
                self.result = result
            def __str__(self):
                return 'DoneWithThisFrameRef(%s)' % (self.result,)

        class DoneWithThisFrameFloat(JitException):
            def __init__(self, result):
                assert lltype.typeOf(result) is lltype.Float
                self.result = result
            def __str__(self):
                return 'DoneWithThisFrameFloat(%s)' % (self.result,)

        class ExitFrameWithExceptionRef(JitException):
            def __init__(self, cpu, value):
                assert lltype.typeOf(value) == cpu.ts.BASETYPE
                self.value = value
            def __str__(self):
                return 'ExitFrameWithExceptionRef(%s)' % (self.value,)

        class ContinueRunningNormally(ContinueRunningNormallyBase):
            def __init__(self, argboxes):
                # accepts boxes as argument, but unpacks them immediately
                # before we raise the exception -- the boxes' values will
                # be modified in a 'finally' by restore_patched_boxes().
                from pypy.jit.metainterp.warmstate import unwrap
                for i, name, ARG in portalfunc_ARGS:
                    v = unwrap(ARG, argboxes[i])
                    setattr(self, name, v)

            def __str__(self):
                return 'ContinueRunningNormally(%s)' % (
                    ', '.join(map(str, self.args)),)

        self.DoneWithThisFrameVoid = DoneWithThisFrameVoid
        self.DoneWithThisFrameInt = DoneWithThisFrameInt
        self.DoneWithThisFrameRef = DoneWithThisFrameRef
        self.DoneWithThisFrameFloat = DoneWithThisFrameFloat
        self.ExitFrameWithExceptionRef = ExitFrameWithExceptionRef
        self.ContinueRunningNormally = ContinueRunningNormally
        self.metainterp_sd.DoneWithThisFrameVoid = DoneWithThisFrameVoid
        self.metainterp_sd.DoneWithThisFrameInt = DoneWithThisFrameInt
        self.metainterp_sd.DoneWithThisFrameRef = DoneWithThisFrameRef
        self.metainterp_sd.DoneWithThisFrameFloat = DoneWithThisFrameFloat
        self.metainterp_sd.ExitFrameWithExceptionRef = ExitFrameWithExceptionRef
        self.metainterp_sd.ContinueRunningNormally = ContinueRunningNormally
    def make_enter_function(self):
        from pypy.jit.metainterp.warmstate import WarmEnterState
        state = WarmEnterState(self)
        maybe_compile_and_run = state.make_entry_point()
        self.state = state

        def crash_in_jit(e):
            if not we_are_translated():
                print "~~~ Crash in JIT!"
                print '~~~ %s: %s' % (e.__class__, e)
                if sys.stdout == sys.__stdout__:
                    import pdb; pdb.post_mortem(sys.exc_info()[2])
                raise
            fatalerror('~~~ Crash in JIT! %s' % (e,), traceback=True)
        crash_in_jit._dont_inline_ = True

        if self.translator.rtyper.type_system.name == 'lltypesystem':
            def maybe_enter_jit(*args):
                try:
                    maybe_compile_and_run(*args)
                except JitException:
                    raise     # go through
                except Exception, e:
                    crash_in_jit(e)
            maybe_enter_jit._always_inline_ = True
        else:
            def maybe_enter_jit(*args):
                maybe_compile_and_run(*args)
            maybe_enter_jit._always_inline_ = True
        self.maybe_enter_jit_fn = maybe_enter_jit

        can_inline = self.state.can_inline_greenargs
        def maybe_enter_from_start(*args):
            if can_inline is not None and not can_inline(*args[:self.num_green_args]):
                maybe_compile_and_run(*args)
        maybe_enter_from_start._always_inline_ = True
        self.maybe_enter_from_start_fn = maybe_enter_from_start


    def make_leave_jit_graph(self):
        self.leave_graph = None
        if self.jitdriver.leave:
            args_s = self.portal_args_s
            from pypy.annotation import model as annmodel
            annhelper = MixLevelHelperAnnotator(self.translator.rtyper)
            s_result = annmodel.s_None
            self.leave_graph = annhelper.getgraph(self.jitdriver.leave,
                                                  args_s, s_result)
            annhelper.finish()
        
    def make_driverhook_graphs(self):
        from pypy.rlib.jit import BaseJitCell
        bk = self.rtyper.annotator.bookkeeper
        classdef = bk.getuniqueclassdef(BaseJitCell)
        s_BaseJitCell_or_None = annmodel.SomeInstance(classdef,
                                                      can_be_None=True)
        s_BaseJitCell_not_None = annmodel.SomeInstance(classdef)
        s_Str = annmodel.SomeString()
        #
        annhelper = MixLevelHelperAnnotator(self.translator.rtyper)
        self.set_jitcell_at_ptr = self._make_hook_graph(
            annhelper, self.jitdriver.set_jitcell_at, annmodel.s_None,
            s_BaseJitCell_not_None)
        self.get_jitcell_at_ptr = self._make_hook_graph(
            annhelper, self.jitdriver.get_jitcell_at, s_BaseJitCell_or_None)
        self.can_inline_ptr = self._make_hook_graph(
            annhelper, self.jitdriver.can_inline, annmodel.s_Bool)
        self.get_printable_location_ptr = self._make_hook_graph(
            annhelper, self.jitdriver.get_printable_location, s_Str)
        self.confirm_enter_jit_ptr = self._make_hook_graph(
            annhelper, self.jitdriver.confirm_enter_jit, annmodel.s_Bool,
            onlygreens=False)
        annhelper.finish()

    def _make_hook_graph(self, annhelper, func, s_result, s_first_arg=None,
                         onlygreens=True):
        if func is None:
            return None
        #
        extra_args_s = []
        if s_first_arg is not None:
            extra_args_s.append(s_first_arg)
        #
        args_s = self.portal_args_s
        if onlygreens:
            args_s = args_s[:len(self.green_args_spec)]
        graph = annhelper.getgraph(func, extra_args_s + args_s, s_result)
        funcptr = annhelper.graph2delayed(graph)
        return funcptr

    def make_args_specification(self):
        graph, block, index = self.jit_merge_point_pos
        op = block.operations[index]
        args = op.args[2:]
        ALLARGS = []
        self.green_args_spec = []
        self.red_args_types = []
        for i, v in enumerate(args):
            TYPE = v.concretetype
            ALLARGS.append(TYPE)
            if i < len(self.jitdriver.greens):
                self.green_args_spec.append(TYPE)
            else:
                self.red_args_types.append(history.getkind(TYPE))
        self.num_green_args = len(self.green_args_spec)
        RESTYPE = graph.getreturnvar().concretetype
        (self.JIT_ENTER_FUNCTYPE,
         self.PTR_JIT_ENTER_FUNCTYPE) = self.cpu.ts.get_FuncType(ALLARGS, lltype.Void)
        (self.PORTAL_FUNCTYPE,
         self.PTR_PORTAL_FUNCTYPE) = self.cpu.ts.get_FuncType(ALLARGS, RESTYPE)
        (_, self.PTR_ASSEMBLER_HELPER_FUNCTYPE) = self.cpu.ts.get_FuncType(
            [lltype.Signed, llmemory.GCREF], RESTYPE)

    def rewrite_can_enter_jit(self):
        FUNC = self.JIT_ENTER_FUNCTYPE
        FUNCPTR = self.PTR_JIT_ENTER_FUNCTYPE
        jit_enter_fnptr = self.helper_func(FUNCPTR, self.maybe_enter_jit_fn)

        graphs = self.translator.graphs
        can_enter_jits = find_can_enter_jit(graphs)
        for graph, block, index in can_enter_jits:
            if graph is self.jit_merge_point_pos[0]:
                continue

            op = block.operations[index]
            greens_v, reds_v = decode_hp_hint_args(op)
            args_v = greens_v + reds_v

            vlist = [Constant(jit_enter_fnptr, FUNCPTR)] + args_v

            v_result = Variable()
            v_result.concretetype = lltype.Void
            newop = SpaceOperation('direct_call', vlist, v_result)
            block.operations[index] = newop

    def helper_func(self, FUNCPTR, func):
        if not self.cpu.translate_support_code:
            return llhelper(FUNCPTR, func)
        FUNC = get_functype(FUNCPTR)
        args_s = [annmodel.lltype_to_annotation(ARG) for ARG in FUNC.ARGS]
        s_result = annmodel.lltype_to_annotation(FUNC.RESULT)
        graph = self.annhelper.getgraph(func, args_s, s_result)
        return self.annhelper.graph2delayed(graph, FUNC)

    def rewrite_jit_merge_point(self, policy):
        #
        # Mutate the original portal graph from this:
        #
        #       def original_portal(..):
        #           stuff
        #           while 1:
        #               jit_merge_point(*args)
        #               more stuff
        #
        # to that:
        #
        #       def original_portal(..):
        #           stuff
        #           return portal_runner(*args)
        #
        #       def portal_runner(*args):
        #           while 1:
        #               try:
        #                   return portal(*args)
        #               except ContinueRunningNormally, e:
        #                   *args = *e.new_args
        #               except DoneWithThisFrame, e:
        #                   return e.return
        #               except ExitFrameWithException, e:
        #                   raise Exception, e.value
        #
        #       def portal(*args):
        #           while 1:
        #               more stuff
        #
        origportalgraph = self.jit_merge_point_pos[0]
        portalgraph = self.portal_graph
        PORTALFUNC = self.PORTAL_FUNCTYPE

        # ____________________________________________________________
        # Prepare the portal_runner() helper
        #
        portal_ptr = self.cpu.ts.functionptr(PORTALFUNC, 'portal',
                                         graph = portalgraph)
        self.portal_ptr = portal_ptr
        portalfunc_ARGS = unrolling_iterable(
            [(i, 'arg%d' % i, ARG) for i, ARG in enumerate(PORTALFUNC.ARGS)])


        rtyper = self.translator.rtyper
        RESULT = PORTALFUNC.RESULT
        result_kind = history.getkind(RESULT)
        ts = self.cpu.ts

        def ll_portal_runner(*args):
            while 1:
                try:
                    self.maybe_enter_from_start_fn(*args)
                    return support.maybe_on_top_of_llinterp(rtyper,
                                                      portal_ptr)(*args)
                except self.ContinueRunningNormally, e:
                    args = ()
                    for _, name, _ in portalfunc_ARGS:
                        v = getattr(e, name)
                        args = args + (v,)
                except self.DoneWithThisFrameVoid:
                    assert result_kind == 'void'
                    return
                except self.DoneWithThisFrameInt, e:
                    assert result_kind == 'int'
                    return lltype.cast_primitive(RESULT, e.result)
                except self.DoneWithThisFrameRef, e:
                    assert result_kind == 'ref'
                    return ts.cast_from_ref(RESULT, e.result)
                except self.DoneWithThisFrameFloat, e:
                    assert result_kind == 'float'
                    return e.result
                except self.ExitFrameWithExceptionRef, e:
                    value = ts.cast_to_baseclass(e.value)
                    if not we_are_translated():
                        raise LLException(ts.get_typeptr(value), value)
                    else:
                        value = cast_base_ptr_to_instance(Exception, value)
                        raise Exception, value

        self.ll_portal_runner = ll_portal_runner # for debugging
        self.portal_runner_ptr = self.helper_func(self.PTR_PORTAL_FUNCTYPE,
                                                  ll_portal_runner)
        self.cpu.portal_calldescr = self.cpu.calldescrof(
            self.PTR_PORTAL_FUNCTYPE.TO,
            self.PTR_PORTAL_FUNCTYPE.TO.ARGS,
            self.PTR_PORTAL_FUNCTYPE.TO.RESULT)

        vinfo = self.metainterp_sd.virtualizable_info

        def assembler_call_helper(failindex, virtualizableref):
            fail_descr = self.cpu.get_fail_descr_from_number(failindex)
            while True:
                try:
                    if vinfo is not None:
                        virtualizable = lltype.cast_opaque_ptr(
                            vinfo.VTYPEPTR, virtualizableref)
                        vinfo.reset_vable_token(virtualizable)
                    loop_token = fail_descr.handle_fail(self.metainterp_sd)
                    fail_descr = self.cpu.execute_token(loop_token)
                except self.ContinueRunningNormally, e:
                    args = ()
                    for _, name, _ in portalfunc_ARGS:
                        v = getattr(e, name)
                        args = args + (v,)
                    return ll_portal_runner(*args)
                except self.DoneWithThisFrameVoid:
                    assert result_kind == 'void'
                    return
                except self.DoneWithThisFrameInt, e:
                    assert result_kind == 'int'
                    return lltype.cast_primitive(RESULT, e.result)
                except self.DoneWithThisFrameRef, e:
                    assert result_kind == 'ref'
                    return ts.cast_from_ref(RESULT, e.result)
                except self.DoneWithThisFrameFloat, e:
                    assert result_kind == 'float'
                    return e.result
                except self.ExitFrameWithExceptionRef, e:
                    value = ts.cast_to_baseclass(e.value)
                    if not we_are_translated():
                        raise LLException(ts.get_typeptr(value), value)
                    else:
                        value = cast_base_ptr_to_instance(Exception, value)
                        raise Exception, value

        self.assembler_call_helper = assembler_call_helper # for debugging
        self.cpu.assembler_helper_ptr = self.helper_func(
            self.PTR_ASSEMBLER_HELPER_FUNCTYPE,
            assembler_call_helper)
        # XXX a bit ugly sticking
        if vinfo is not None:
            self.cpu.index_of_virtualizable = (vinfo.index_of_virtualizable -
                                               self.num_green_args)
        else:
            self.cpu.index_of_virtualizable = -1

        # ____________________________________________________________
        # Now mutate origportalgraph to end with a call to portal_runner_ptr
        #
        _, origblock, origindex = self.jit_merge_point_pos
        op = origblock.operations[origindex]
        assert op.opname == 'jit_marker'
        assert op.args[0].value == 'jit_merge_point'
        greens_v, reds_v = decode_hp_hint_args(op)
        vlist = [Constant(self.portal_runner_ptr, self.PTR_PORTAL_FUNCTYPE)]
        vlist += greens_v
        vlist += reds_v
        v_result = Variable()
        v_result.concretetype = PORTALFUNC.RESULT
        newop = SpaceOperation('direct_call', vlist, v_result)
        del origblock.operations[origindex:]
        origblock.operations.append(newop)
        origblock.exitswitch = None
        origblock.recloseblock(Link([v_result], origportalgraph.returnblock))
        checkgraph(origportalgraph)

    def add_finish(self):
        def finish():
            if self.metainterp_sd.profiler.initialized:
                self.metainterp_sd.profiler.finish()
            self.metainterp_sd.cpu.finish_once()
        
        if self.cpu.translate_support_code:
            call_final_function(self.translator, finish,
                                annhelper = self.annhelper)

    def rewrite_set_param(self):
        closures = {}
        graphs = self.translator.graphs
        _, PTR_SET_PARAM_FUNCTYPE = self.cpu.ts.get_FuncType([lltype.Signed],
                                                             lltype.Void)
        def make_closure(fullfuncname):
            state = self.state
            def closure(i):
                getattr(state, fullfuncname)(i)
            funcptr = self.helper_func(PTR_SET_PARAM_FUNCTYPE, closure)
            return Constant(funcptr, PTR_SET_PARAM_FUNCTYPE)
        #
        for graph, block, i in find_set_param(graphs):
            op = block.operations[i]
            assert op.args[1].value == self.jitdriver
            funcname = op.args[2].value
            if funcname not in closures:
                closures[funcname] = make_closure('set_param_' + funcname)
            op.opname = 'direct_call'
            op.args[:3] = [closures[funcname]]

    def rewrite_force_virtual(self):
        if self.cpu.ts.name != 'lltype':
            py.test.skip("rewrite_force_virtual: port it to ootype")
        all_graphs = self.translator.graphs
        vrefinfo = self.metainterp_sd.virtualref_info
        vrefinfo.replace_force_virtual_with_call(all_graphs)


def decode_hp_hint_args(op):
    # Returns (list-of-green-vars, list-of-red-vars) without Voids.
    assert op.opname == 'jit_marker'
    jitdriver = op.args[1].value
    numgreens = len(jitdriver.greens)
    numreds = len(jitdriver.reds)
    greens_v = op.args[2:2+numgreens]
    reds_v = op.args[2+numgreens:]
    assert len(reds_v) == numreds
    return ([v for v in greens_v if v.concretetype is not lltype.Void],
            [v for v in reds_v if v.concretetype is not lltype.Void])
