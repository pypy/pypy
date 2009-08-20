import sys
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
from pypy.rlib.jit import PARAMETERS
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.debug import debug_print
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.translator.simplify import get_funcobj, get_functype
from pypy.translator.unsimplify import call_final_function

from pypy.jit.metainterp import support, history, pyjitpl, gc
from pypy.jit.metainterp.pyjitpl import MetaInterpStaticData, MetaInterp
from pypy.jit.metainterp.policy import JitPolicy
from pypy.jit.metainterp.typesystem import LLTypeHelper, OOTypeHelper
from pypy.jit.metainterp.jitprof import Profiler

# ____________________________________________________________
# Bootstrapping

def apply_jit(translator, backend_name="auto", debug_level="steps", **kwds):
    if 'CPUClass' not in kwds:
        from pypy.jit.backend.detect_cpu import getcpuclass
        kwds['CPUClass'] = getcpuclass(backend_name)
    pyjitpl.DEBUG = pyjitpl._DEBUG_LEVEL[debug_level]
    if debug_level != "off":
        profile = Profiler
    else:
        profile = None
    warmrunnerdesc = WarmRunnerDesc(translator,
                                    translate_support_code=True,
                                    listops=True,
                                    #inline=True,
                                    profile=profile,
                                    **kwds)
    warmrunnerdesc.finish()
    translator.warmrunnerdesc = warmrunnerdesc    # for later debugging

def ll_meta_interp(function, args, backendopt=False, type_system='lltype',
                   **kwds):
    interp, graph = get_interpreter(function, args,
                                    backendopt=False,  # will be done below
                                    type_system=type_system)
    clear_tcache()
    return jittify_and_run(interp, graph, args, backendopt=backendopt, **kwds)

def jittify_and_run(interp, graph, args, repeat=1, hash_bits=None, backendopt=False,
                    **kwds):
    translator = interp.typer.annotator.translator
    translator.config.translation.gc = "boehm"
    warmrunnerdesc = WarmRunnerDesc(translator, backendopt=backendopt, **kwds)
    warmrunnerdesc.state.set_param_threshold(3)          # for tests
    warmrunnerdesc.state.set_param_trace_eagerness(2)    # for tests
    warmrunnerdesc.state.create_tables_now()             # for tests
    if hash_bits:
        warmrunnerdesc.state.set_param_hash_bits(hash_bits)
    warmrunnerdesc.finish()
    res = interp.eval_graph(graph, args)
    warmrunnerdesc.metainterp_sd.profiler.finish()
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

def debug_checks():
    stats = get_stats()
    stats.maybe_view()
    stats.check_consistency()

class JitException(Exception):
    _go_through_llinterp_uncaught_ = True     # ugh

class CannotInlineCanEnterJit(JitException):
    pass

# ____________________________________________________________

class WarmRunnerDesc:

    def __init__(self, translator, policy=None, backendopt=True, **kwds):
        pyjitpl._warmrunnerdesc = self   # this is a global for debugging only!
        if policy is None:
            policy = JitPolicy()
        self.set_translator(translator)
        self.find_portal()
        if backendopt:
            self.prejit_optimizations(policy)

        self.build_meta_interp(**kwds)
        self.make_args_specification()
        self.rewrite_jit_merge_point()
        self.make_driverhook_graph()
        if self.jitdriver.virtualizables:
            from pypy.jit.metainterp.virtualizable import VirtualizableInfo
            self.metainterp_sd.virtualizable_info = VirtualizableInfo(self)
        self.metainterp_sd.generate_bytecode(policy, self.ts)
        self.make_enter_function()
        self.rewrite_can_enter_jit()
        self.rewrite_set_param()
        self.add_profiler_finish()
        self.metainterp_sd.finish_setup()

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
        if translator.rtyper.type_system.name == 'lltypesystem':
            self.ts = LLTypeHelper()
        else:
            assert translator.rtyper.type_system.name == 'ootypesystem'
            self.ts = OOTypeHelper()
        self.gcdescr = gc.get_description(translator.config)

    def find_portal(self):
        graphs = self.translator.graphs
        self.jit_merge_point_pos = find_jit_merge_point(graphs)
        graph, block, pos = self.jit_merge_point_pos
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
        if hasattr(graph, "func"):
            graph.func._dont_inline_ = True
        self.jitdriver = block.operations[pos].args[1].value

    def prejit_optimizations(self, policy):
        from pypy.translator.backendopt.all import backend_optimizations
        graphs = find_all_graphs(self.portal_graph, policy, self.translator)
        backend_optimizations(self.translator,
                              graphs=graphs,
                              merge_if_blocks=True,
                              constfold=True,
                              raisingop2direct_call=False,
                              remove_asserts=True,
                              really_remove_asserts=True)

    def build_meta_interp(self, CPUClass=None, translate_support_code=False,
                          view="auto", optimizer=None, profile=None, **kwds):
        assert CPUClass is not None
        opt = history.Options(**kwds)
        self.stats = history.Stats()
        if translate_support_code:
            self.annhelper = MixLevelHelperAnnotator(self.translator.rtyper)
            annhelper = self.annhelper
        else:
            annhelper = None
        cpu = CPUClass(self.translator.rtyper, self.stats,
                       translate_support_code, annhelper, self.gcdescr)
        self.cpu = cpu
        self.metainterp_sd = MetaInterpStaticData(self.portal_graph,
                                                  self.translator.graphs, cpu,
                                                  self.stats, opt,
                                                  optimizer=optimizer,
                                                  profile=profile,
                                                  warmrunnerdesc=self)

    def make_enter_function(self):
        WarmEnterState = make_state_class(self)
        state = WarmEnterState()
        self.state = state

        def crash_in_jit(e):
            if not we_are_translated():
                print "~~~ Crash in JIT!"
                print '~~~ %s: %s' % (e.__class__, e)
                if sys.stdout == sys.__stdout__:
                    import pdb; pdb.post_mortem(sys.exc_info()[2])
                raise
            debug_print('~~~ Crash in JIT!')
            debug_print('~~~ %s' % (e,))
            raise history.CrashInJIT("crash in JIT")
        crash_in_jit._dont_inline_ = True

        if self.translator.rtyper.type_system.name == 'lltypesystem':
            def maybe_enter_jit(*args):
                try:
                    state.maybe_compile_and_run(*args)
                except JitException:
                    raise     # go through
                except Exception, e:
                    crash_in_jit(e)
            maybe_enter_jit._always_inline_ = True
        else:
            def maybe_enter_jit(*args):
                state.maybe_compile_and_run(*args)
            maybe_enter_jit._always_inline_ = True

        self.maybe_enter_jit_fn = maybe_enter_jit

    def make_driverhook_graph(self):
        self.can_inline_ptr = self._make_hook_graph(
            self.jitdriver.can_inline, bool)
        self.get_printable_location_ptr = self._make_hook_graph(
            self.jitdriver.get_printable_location, str)

    def _make_hook_graph(self, func, rettype):
        from pypy.annotation.signature import annotationoftype
        if func is None:
            return None
        annhelper = MixLevelHelperAnnotator(self.translator.rtyper)
        s_result = annotationoftype(rettype)
        RETTYPE = annhelper.rtyper.getrepr(s_result).lowleveltype
        FUNC, PTR = self.ts.get_FuncType(self.green_args_spec, RETTYPE)
        args_s = [annmodel.lltype_to_annotation(ARG) for ARG in FUNC.ARGS]
        graph = annhelper.getgraph(func, args_s, s_result)
        funcptr = annhelper.graph2delayed(graph, FUNC)
        annhelper.finish()
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
        RESTYPE = graph.getreturnvar().concretetype
        (self.JIT_ENTER_FUNCTYPE,
         self.PTR_JIT_ENTER_FUNCTYPE) = self.ts.get_FuncType(ALLARGS, lltype.Void)
        (self.PORTAL_FUNCTYPE,
         self.PTR_PORTAL_FUNCTYPE) = self.ts.get_FuncType(ALLARGS, RESTYPE)
        

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

    def rewrite_jit_merge_point(self):
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
        portal_ptr = self.ts.functionptr(PORTALFUNC, 'portal',
                                         graph = portalgraph)
        portalfunc_ARGS = unrolling_iterable(
            [(i, 'arg%d' % i, ARG) for i, ARG in enumerate(PORTALFUNC.ARGS)])

        class DoneWithThisFrameVoid(JitException):
            def __str__(self):
                return 'DoneWithThisFrameVoid()'

        class DoneWithThisFrameInt(JitException):
            def __init__(self, result):
                assert lltype.typeOf(result) is lltype.Signed
                self.result = result
            def __str__(self):
                return 'DoneWithThisFrameInt(%s)' % (self.result,)

        class DoneWithThisFramePtr(JitException):
            def __init__(self, result):
                assert lltype.typeOf(result) == llmemory.GCREF
                self.result = result
            def __str__(self):
                return 'DoneWithThisFramePtr(%s)' % (self.result,)

        class DoneWithThisFrameObj(JitException):
            def __init__(self, result):
                assert ootype.typeOf(result) == ootype.Object
                self.result = result
            def __str__(self):
                return 'DoneWithThisFrameObj(%s)' % (self.result,)

        class ExitFrameWithExceptionPtr(JitException):
            def __init__(self, value):
                assert lltype.typeOf(value) == llmemory.GCREF
                self.value = value
            def __str__(self):
                return 'ExitFrameWithExceptionPtr(%s)' % (self.value,)

        class ExitFrameWithExceptionObj(JitException):
            def __init__(self, value):
                assert lltype.typeOf(value) == ootype.Object
                self.value = value
            def __str__(self):
                return 'ExitFrameWithExceptionObj(%s)' % (self.value,)

        class ContinueRunningNormally(JitException):
            def __init__(self, argboxes):
                # accepts boxes as argument, but unpacks them immediately
                # before we raise the exception -- the boxes' values will
                # be modified in a 'finally' by restore_patched_boxes().
                for i, name, ARG in portalfunc_ARGS:
                    v = unwrap(ARG, argboxes[i])
                    setattr(self, name, v)

            def __str__(self):
                return 'ContinueRunningNormally(%s)' % (
                    ', '.join(map(str, self.args)),)

        self.DoneWithThisFrameVoid = DoneWithThisFrameVoid
        self.DoneWithThisFrameInt = DoneWithThisFrameInt
        self.DoneWithThisFramePtr = DoneWithThisFramePtr
        self.DoneWithThisFrameObj = DoneWithThisFrameObj
        self.ExitFrameWithExceptionPtr = ExitFrameWithExceptionPtr
        self.ExitFrameWithExceptionObj = ExitFrameWithExceptionObj
        self.ContinueRunningNormally = ContinueRunningNormally
        self.metainterp_sd.DoneWithThisFrameVoid = DoneWithThisFrameVoid
        self.metainterp_sd.DoneWithThisFrameInt = DoneWithThisFrameInt
        self.metainterp_sd.DoneWithThisFramePtr = DoneWithThisFramePtr
        self.metainterp_sd.DoneWithThisFrameObj = DoneWithThisFrameObj
        self.metainterp_sd.ExitFrameWithExceptionPtr = ExitFrameWithExceptionPtr
        self.metainterp_sd.ExitFrameWithExceptionObj = ExitFrameWithExceptionObj
        self.metainterp_sd.ContinueRunningNormally = ContinueRunningNormally
        rtyper = self.translator.rtyper
        RESULT = PORTALFUNC.RESULT
        result_kind = history.getkind(RESULT)
        is_oo = self.cpu.is_oo

        def ll_portal_runner(*args):
            while 1:
                try:
                    return support.maybe_on_top_of_llinterp(rtyper,
                                                      portal_ptr)(*args)
                except ContinueRunningNormally, e:
                    args = ()
                    for _, name, _ in portalfunc_ARGS:
                        v = getattr(e, name)
                        args = args + (v,)
                except DoneWithThisFrameVoid:
                    assert result_kind == 'void'
                    return
                except DoneWithThisFrameInt, e:
                    assert result_kind == 'int'
                    return lltype.cast_primitive(RESULT, e.result)
                except DoneWithThisFramePtr, e:
                    assert result_kind == 'ptr'
                    return lltype.cast_opaque_ptr(RESULT, e.result)
                except DoneWithThisFrameObj, e:
                    assert result_kind == 'obj'
                    return ootype.cast_from_object(RESULT, e.result)
                except ExitFrameWithExceptionPtr, e:
                    assert not is_oo
                    value = lltype.cast_opaque_ptr(lltype.Ptr(rclass.OBJECT),
                                                   e.value)
                    if not we_are_translated():
                        raise LLException(value.typeptr, value)
                    else:
                        value = cast_base_ptr_to_instance(Exception, value)
                        raise Exception, value
                except ExitFrameWithExceptionObj, e:
                    assert is_oo
                    value = ootype.cast_from_object(ootype.ROOT, e.value)
                    if not we_are_translated():
                        raise LLException(ootype.classof(value), value)
                    else:
                        value = cast_base_ptr_to_instance(Exception, value)
                        raise Exception, value
        ll_portal_runner._recursive_portal_call_ = True

        portal_runner_ptr = self.helper_func(self.PTR_PORTAL_FUNCTYPE,
                                             ll_portal_runner)

        # ____________________________________________________________
        # Now mutate origportalgraph to end with a call to portal_runner_ptr
        #
        _, origblock, origindex = self.jit_merge_point_pos
        op = origblock.operations[origindex]
        assert op.opname == 'jit_marker'
        assert op.args[0].value == 'jit_merge_point'
        greens_v, reds_v = decode_hp_hint_args(op)
        vlist = [Constant(portal_runner_ptr, self.PTR_PORTAL_FUNCTYPE)]
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

    def add_profiler_finish(self):
        def finish_profiler():
            if self.metainterp_sd.profiler.initialized:
                self.metainterp_sd.profiler.finish()
        
        if self.cpu.translate_support_code:
            call_final_function(self.translator, finish_profiler,
                                annhelper = self.annhelper)

    def rewrite_set_param(self):
        closures = {}
        graphs = self.translator.graphs
        _, PTR_SET_PARAM_FUNCTYPE = self.ts.get_FuncType([lltype.Signed],
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


def find_all_graphs(portal, policy, translator):
    from pypy.translator.simplify import get_graph
    all_graphs = [portal]
    seen = set([portal])
    todo = [portal]
    while todo:
        top_graph = todo.pop()
        for _, op in top_graph.iterblockops():
            if op.opname not in ("direct_call", "indirect_call", "oosend"):
                continue
            kind = policy.guess_call_kind(op)
            if kind != "regular":
                continue
            for graph in policy.graphs_from(op):
                if graph in seen:
                    continue
                if policy.look_inside_graph(graph):
                    todo.append(graph)
                    all_graphs.append(graph)
                    seen.add(graph)
    return all_graphs



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

def unwrap(TYPE, box):
    if TYPE is lltype.Void:
        return None
    if isinstance(TYPE, lltype.Ptr):
        return box.getptr(TYPE)
    if isinstance(TYPE, ootype.OOType):
        return ootype.cast_from_object(TYPE, box.getobj())
    else:
        return lltype.cast_primitive(TYPE, box.getint())
unwrap._annspecialcase_ = 'specialize:arg(0)'

def wrap(cpu, value, in_const_box=False):
    if isinstance(lltype.typeOf(value), lltype.Ptr):
        if lltype.typeOf(value).TO._gckind == 'gc':
            value = lltype.cast_opaque_ptr(llmemory.GCREF, value)
            if in_const_box:
                return history.ConstPtr(value)
            else:
                return history.BoxPtr(value)
        else:
            adr = llmemory.cast_ptr_to_adr(value)
            value = cpu.cast_adr_to_int(adr)
            # fall through to the end of the function
    elif isinstance(lltype.typeOf(value), ootype.OOType):
        value = ootype.cast_to_object(value)
        if in_const_box:
            return history.ConstObj(value)
        else:
            return history.BoxObj(value)
    else:
        value = intmask(value)
    if in_const_box:
        return history.ConstInt(value)
    else:
        return history.BoxInt(value)
wrap._annspecialcase_ = 'specialize:ll'

def equal_whatever(TYPE, x, y):
    if isinstance(TYPE, lltype.Ptr):
        if TYPE.TO is rstr.STR or TYPE.TO is rstr.UNICODE:
            return rstr.LLHelpers.ll_streq(x, y)
    return x == y
equal_whatever._annspecialcase_ = 'specialize:arg(0)'

def cast_whatever_to_int(TYPE, x):
    if isinstance(TYPE, lltype.Ptr):
        # only supports strings, unicodes and regular instances *with a hash
        # cache*.  The 'jit_merge_point' hint forces a hash cache to appear.
        return x.gethash()
    elif TYPE is ootype.String or TYPE is ootype.Unicode:
        return ootype.oohash(x)
    elif isinstance(TYPE, ootype.OOType):
        return ootype.ooidentityhash(x)
    else:
        return lltype.cast_primitive(lltype.Signed, x)
cast_whatever_to_int._annspecialcase_ = 'specialize:arg(0)'

# ____________________________________________________________

def make_state_class(warmrunnerdesc):
    jitdriver = warmrunnerdesc.jitdriver
    num_green_args = len(jitdriver.greens)
    warmrunnerdesc.num_green_args = num_green_args
    green_args_spec = unrolling_iterable(warmrunnerdesc.green_args_spec)
    green_args_names = unrolling_iterable(jitdriver.greens)
    green_args_spec_names = unrolling_iterable(zip(
        warmrunnerdesc.green_args_spec, jitdriver.greens))
    red_args_types = unrolling_iterable(warmrunnerdesc.red_args_types)
    #
    metainterp_sd = warmrunnerdesc.metainterp_sd
    vinfo = metainterp_sd.virtualizable_info
    if vinfo is None:
        vable_static_fields = []
        vable_array_fields = []
    else:
        vable_static_fields = unrolling_iterable(
            zip(vinfo.static_extra_types, vinfo.static_fields))
        vable_array_fields = unrolling_iterable(
            zip(vinfo.arrayitem_extra_types, vinfo.array_fields))
    #
    if num_green_args:
        MAX_HASH_TABLE_BITS = 28
    else:
        MAX_HASH_TABLE_BITS = 1
    THRESHOLD_LIMIT = sys.maxint // 2
    #
    getlength = warmrunnerdesc.ts.getlength
    getarrayitem = warmrunnerdesc.ts.getarrayitem
    setarrayitem = warmrunnerdesc.ts.setarrayitem
    #
    rtyper = warmrunnerdesc.translator.rtyper
    can_inline_ptr = warmrunnerdesc.can_inline_ptr
    get_printable_location_ptr = warmrunnerdesc.get_printable_location_ptr
    #
    class MachineCodeEntryPoint(object):
        next = None    # linked list
        def __init__(self, bridge, *greenargs):
            self.bridge = bridge
            i = 0
            for name in green_args_names:
                setattr(self, 'green_' + name, greenargs[i])
                i = i + 1
        def equalkey(self, *greenargs):
            i = 0
            for TYPE, name in green_args_spec_names:
                myvalue = getattr(self, 'green_' + name)
                if not equal_whatever(TYPE, myvalue, greenargs[i]):
                    return False
                i = i + 1
            return True
        def set_future_values(self, *redargs):
            i = 0
            for typecode in red_args_types:
                set_future_value(i, redargs[i], typecode)
                i = i + 1
            if vinfo is not None:
                virtualizable = redargs[vinfo.index_of_virtualizable -
                                        num_green_args]
                virtualizable = vinfo.cast_to_vtype(virtualizable)
                for typecode, fieldname in vable_static_fields:
                    x = getattr(virtualizable, fieldname)
                    set_future_value(i, x, typecode)
                    i = i + 1
                for typecode, fieldname in vable_array_fields:
                    lst = getattr(virtualizable, fieldname)
                    for j in range(getlength(lst)):
                        x = getarrayitem(lst, j)
                        set_future_value(i, x, typecode)
                        i = i + 1

    def set_future_value(j, value, typecode):
        cpu = metainterp_sd.cpu
        if typecode == 'ptr':
            ptrvalue = lltype.cast_opaque_ptr(llmemory.GCREF, value)
            cpu.set_future_value_ptr(j, ptrvalue)
        elif typecode == 'obj':
            objvalue = ootype.cast_to_object(value)
            cpu.set_future_value_obj(j, objvalue)
        elif typecode == 'int':
            intvalue = lltype.cast_primitive(lltype.Signed, value)
            cpu.set_future_value_int(j, intvalue)
        else:
            assert False
    set_future_value._annspecialcase_ = 'specialize:ll_and_arg(2)'

    class WarmEnterState:
        def __init__(self):
            # initialize the state with the default values of the
            # parameters specified in rlib/jit.py
            for name, default_value in PARAMETERS.items():
                meth = getattr(self, 'set_param_' + name)
                meth(default_value)

        def set_param_threshold(self, threshold):
            if threshold < 2:
                threshold = 2
            self.increment_threshold = (THRESHOLD_LIMIT // threshold) + 1
            # the number is at least 1, and at most about half THRESHOLD_LIMIT

        def set_param_trace_eagerness(self, value):
            self.trace_eagerness = value

        def set_param_hash_bits(self, value):
            if value < 1:
                value = 1
            elif value > MAX_HASH_TABLE_BITS:
                value = MAX_HASH_TABLE_BITS
            # the tables are initialized with the correct size only in
            # create_tables_now()
            self.hashbits = value
            self.hashtablemask = 0
            self.mccounters = [0]
            self.mcentrypoints = [None]
            # invariant: (self.mccounters[j] < 0) if and only if
            #            (self.mcentrypoints[j] is not None)

        def create_tables_now(self):
            count = 1 << self.hashbits
            self.hashtablemask = count - 1
            self.mccounters = [0] * count
            self.mcentrypoints = [None] * count

        # Only use the hash of the arguments as the profiling key.
        # Indeed, this is all a heuristic, so if things are designed
        # correctly, the occasional mistake due to hash collision is
        # not too bad.

        def maybe_compile_and_run(self, *args):
            # get the greenargs and look for the cell corresponding to the hash
            greenargs = args[:num_green_args]
            argshash = self.getkeyhash(*greenargs) & self.hashtablemask
            counter = self.mccounters[argshash]
            if counter >= 0:
                # update the profiling counter
                n = counter + self.increment_threshold
                if n <= THRESHOLD_LIMIT:       # bound not reached
                    self.mccounters[argshash] = n
                    return
                if self.hashtablemask == 0: # must really create the tables now
                    self.create_tables_now()
                    return
                metainterp = MetaInterp(metainterp_sd)
                loop = metainterp.compile_and_run_once(*args)
            else:
                # machine code was already compiled for these greenargs
                # (or we have a hash collision)
                cell = self.mcentrypoints[argshash]
                if not cell.equalkey(*greenargs):
                    # hash collision
                    loop = self.handle_hash_collision(cell, argshash, *args)
                    if loop is None:
                        return
                else:
                    # get the assembler and fill in the boxes
                    cell.set_future_values(*args[num_green_args:])
                    loop = cell.bridge
            # ---------- execute assembler ----------
            while True:     # until interrupted by an exception
                metainterp_sd.profiler.start_running()
                fail_op = metainterp_sd.cpu.execute_operations(loop)
                metainterp_sd.profiler.end_running()
                loop = fail_op.descr.handle_fail_op(metainterp_sd, fail_op)
        maybe_compile_and_run._dont_inline_ = True

        def handle_hash_collision(self, firstcell, argshash, *args):
            greenargs = args[:num_green_args]
            # search the linked list for the correct cell
            cell = firstcell
            while cell.next is not None:
                nextcell = cell.next
                if nextcell.equalkey(*greenargs):
                    # found, move to the front of the linked list
                    cell.next = nextcell.next
                    nextcell.next = firstcell
                    self.mcentrypoints[argshash] = nextcell
                    nextcell.set_future_values(*args[num_green_args:])
                    return nextcell.bridge
                cell = nextcell
            # not found at all, do profiling
            counter = self.mccounters[argshash]
            assert counter < 0          # by invariant
            n = counter + self.increment_threshold
            if n < 0:      # bound not reached
                self.mccounters[argshash] = n
                return None
            metainterp = MetaInterp(metainterp_sd)
            return metainterp.compile_and_run_once(*args)
        handle_hash_collision._dont_inline_ = True

        def unwrap_greenkey(self, greenkey):
            greenargs = ()
            i = 0
            for TYPE in green_args_spec:
                value = unwrap(TYPE, greenkey[i])
                greenargs += (value,)
                i = i + 1
            return greenargs
        unwrap_greenkey._always_inline_ = True

        def comparekey(greenargs1, greenargs2):
            i = 0
            for TYPE in green_args_spec:
                if not equal_whatever(TYPE, greenargs1[i], greenargs2[i]):
                    return False
                i = i + 1
            return True
        comparekey = staticmethod(comparekey)

        def hashkey(greenargs):
            return intmask(WarmEnterState.getkeyhash(*greenargs))
        hashkey = staticmethod(hashkey)

        def getkeyhash(*greenargs):
            result = r_uint(0x345678)
            i = 0
            mult = r_uint(1000003)
            for TYPE in green_args_spec:
                if i > 0:
                    result = result * mult
                    mult = mult + 82520 + 2*len(greenargs)
                item = greenargs[i]
                result = result ^ cast_whatever_to_int(TYPE, item)
                i = i + 1
            return result         # returns a r_uint
        getkeyhash._always_inline_ = True
        getkeyhash = staticmethod(getkeyhash)

        def must_compile_from_failure(self, key):
            key.counter += 1
            return key.counter >= self.trace_eagerness

        def attach_unoptimized_bridge_from_interp(self, greenkey, bridge):
            greenargs = self.unwrap_greenkey(greenkey)
            newcell = MachineCodeEntryPoint(bridge, *greenargs)
            argshash = self.getkeyhash(*greenargs) & self.hashtablemask
            oldcell = self.mcentrypoints[argshash]
            newcell.next = oldcell     # link
            self.mcentrypoints[argshash] = newcell
            self.mccounters[argshash] = -THRESHOLD_LIMIT-1

        if can_inline_ptr is None:
            def can_inline_callable(self, greenkey):
                return True
        else:
            def can_inline_callable(self, greenkey):
                args = self.unwrap_greenkey(greenkey)
                fn = support.maybe_on_top_of_llinterp(rtyper, can_inline_ptr)
                return fn(*args)

        if get_printable_location_ptr is None:
            def get_location_str(self, greenkey):
                return '(no jitdriver.get_printable_location!)'
        else:
            def get_location_str(self, greenkey):
                args = self.unwrap_greenkey(greenkey)
                fn = support.maybe_on_top_of_llinterp(rtyper,
                                                  get_printable_location_ptr)
                res = fn(*args)
                if we_are_translated() or not isinstance(res, str):
                    res = hlstr(res)
                return res

    return WarmEnterState
