#
# Contains the logic to decide, based on the policy, which graphs
# to transform to JitCodes or not.
#

from rpython.jit.codewriter import support
from rpython.jit.codewriter.jitcode import JitCode
from rpython.jit.codewriter.effectinfo import (VirtualizableAnalyzer,
    QuasiImmutAnalyzer, RandomEffectsAnalyzer, effectinfo_from_writeanalyze,
    EffectInfo, CallInfoCollection)
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.translator.backendopt.canraise import RaiseAnalyzer
from rpython.translator.backendopt.writeanalyze import ReadWriteAnalyzer
from rpython.translator.backendopt.graphanalyze import DependencyTracker


class CallControl(object):
    virtualref_info = None     # optionally set from outside
    has_libffi_call = False    # default value

    def __init__(self, cpu=None, jitdrivers_sd=[]):
        assert isinstance(jitdrivers_sd, list)   # debugging
        self.cpu = cpu
        self.jitdrivers_sd = jitdrivers_sd
        self.jitcodes = {}             # map {graph: jitcode}
        self.unfinished_graphs = []    # list of graphs with pending jitcodes
        self.callinfocollection = CallInfoCollection()
        if hasattr(cpu, 'rtyper'):     # for tests
            self.rtyper = cpu.rtyper
            translator = self.rtyper.annotator.translator
            self.raise_analyzer = RaiseAnalyzer(translator)
            self.readwrite_analyzer = ReadWriteAnalyzer(translator)
            self.virtualizable_analyzer = VirtualizableAnalyzer(translator)
            self.quasiimmut_analyzer = QuasiImmutAnalyzer(translator)
            self.randomeffects_analyzer = RandomEffectsAnalyzer(translator)
            self.seen = DependencyTracker(self.readwrite_analyzer)
        else:
            self.seen = None
        #
        for index, jd in enumerate(jitdrivers_sd):
            jd.index = index

    def find_all_graphs(self, policy):
        try:
            return self.candidate_graphs
        except AttributeError:
            pass

        is_candidate = policy.look_inside_graph

        assert len(self.jitdrivers_sd) > 0
        todo = [jd.portal_graph for jd in self.jitdrivers_sd]
        if hasattr(self, 'rtyper'):
            for oopspec_name, ll_args, ll_res in support.inline_calls_to:
                c_func, _ = support.builtin_func_for_spec(self.rtyper,
                                                          oopspec_name,
                                                          ll_args, ll_res)
                todo.append(c_func.value._obj.graph)
        candidate_graphs = set(todo)

        def callers():
            graph = top_graph
            print graph
            while graph in coming_from:
                graph = coming_from[graph]
                print '<-', graph
        coming_from = {}

        while todo:
            top_graph = todo.pop()
            for _, op in top_graph.iterblockops():
                if op.opname not in ("direct_call", "indirect_call"):
                    continue
                kind = self.guess_call_kind(op, is_candidate)
                # use callers() to view the calling chain in pdb
                if kind != "regular":
                    continue
                for graph in self.graphs_from(op, is_candidate):
                    if graph in candidate_graphs:
                        continue
                    assert is_candidate(graph)
                    todo.append(graph)
                    candidate_graphs.add(graph)
                    coming_from[graph] = top_graph
        self.candidate_graphs = candidate_graphs
        return candidate_graphs

    def graphs_from(self, op, is_candidate=None):
        if is_candidate is None:
            is_candidate = self.is_candidate
        if op.opname == 'direct_call':
            funcobj = op.args[0].value._obj
            graph = funcobj.graph
            if is_candidate(graph):
                return [graph]     # common case: look inside this graph
        else:
            assert op.opname == 'indirect_call'
            graphs = op.args[-1].value
            if graphs is not None:
                result = []
                for graph in graphs:
                    if is_candidate(graph):
                        result.append(graph)
                if result:
                    return result  # common case: look inside these graphs,
                                   # and ignore the others if there are any
        # residual call case: we don't need to look into any graph
        return None

    def guess_call_kind(self, op, is_candidate=None):
        if op.opname == 'direct_call':
            funcptr = op.args[0].value
            if self.jitdriver_sd_from_portal_runner_ptr(funcptr) is not None:
                return 'recursive'
            funcobj = funcptr._obj
            if getattr(funcobj, 'graph', None) is None:
                return 'residual'
            targetgraph = funcobj.graph
            if hasattr(targetgraph, 'func'):
                # must never produce JitCode for a function with
                # _gctransformer_hint_close_stack_ set!
                if getattr(targetgraph.func,
                           '_gctransformer_hint_close_stack_', False):
                    return 'residual'
                if hasattr(targetgraph.func, 'oopspec'):
                    return 'builtin'
        if self.graphs_from(op, is_candidate) is None:
            return 'residual'
        return 'regular'

    def is_candidate(self, graph):
        # used only after find_all_graphs()
        return graph in self.candidate_graphs

    def grab_initial_jitcodes(self):
        for jd in self.jitdrivers_sd:
            jd.mainjitcode = self.get_jitcode(jd.portal_graph)
            jd.mainjitcode.is_portal = True

    def enum_pending_graphs(self):
        while self.unfinished_graphs:
            graph = self.unfinished_graphs.pop()
            yield graph, self.jitcodes[graph]

    def get_jitcode(self, graph, called_from=None):
        # 'called_from' is only one of the callers, used for debugging.
        try:
            return self.jitcodes[graph]
        except KeyError:
            # must never produce JitCode for a function with
            # _gctransformer_hint_close_stack_ set!
            if hasattr(graph, 'func') and getattr(graph.func,
                    '_gctransformer_hint_close_stack_', False):
                raise AssertionError(
                    '%s has _gctransformer_hint_close_stack_' % (graph,))
            #
            fnaddr, calldescr = self.get_jitcode_calldescr(graph)
            jitcode = JitCode(graph.name, fnaddr, calldescr,
                              called_from=called_from)
            self.jitcodes[graph] = jitcode
            self.unfinished_graphs.append(graph)
            return jitcode

    def get_jitcode_calldescr(self, graph):
        """Return the calldescr that describes calls to the 'graph'.
        This returns a calldescr that is appropriate to attach to the
        jitcode corresponding to 'graph'.  It has no extra effectinfo,
        because it is not needed there; it is only used by the blackhole
        interp to really do the call corresponding to 'inline_call' ops.
        """
        fnptr = self.rtyper.type_system.getcallable(graph)
        FUNC = lltype.typeOf(fnptr).TO
        assert self.rtyper.type_system.name == "lltypesystem"
        fnaddr = llmemory.cast_ptr_to_adr(fnptr)
        NON_VOID_ARGS = [ARG for ARG in FUNC.ARGS if ARG is not lltype.Void]
        calldescr = self.cpu.calldescrof(FUNC, tuple(NON_VOID_ARGS),
                                         FUNC.RESULT, EffectInfo.MOST_GENERAL)
        return (fnaddr, calldescr)

    def getcalldescr(self, op, oopspecindex=EffectInfo.OS_NONE,
                     extraeffect=None):
        """Return the calldescr that describes all calls done by 'op'.
        This returns a calldescr that we can put in the corresponding
        call operation in the calling jitcode.  It gets an effectinfo
        describing the effect of the call: which field types it may
        change, whether it can force virtualizables, whether it can
        raise, etc.
        """
        NON_VOID_ARGS = [x.concretetype for x in op.args[1:]
                                        if x.concretetype is not lltype.Void]
        RESULT = op.result.concretetype
        # check the number and type of arguments
        FUNC = op.args[0].concretetype.TO
        ARGS = FUNC.ARGS
        if NON_VOID_ARGS != [T for T in ARGS if T is not lltype.Void]:
            raise Exception(
                "in operation %r: caling a function with signature %r, "
                "but passing actual arguments (ignoring voids) of types %r"
                % (op, FUNC, NON_VOID_ARGS))
        if RESULT != FUNC.RESULT:
            raise Exception(
                "in operation %r: caling a function with signature %r, "
                "but the actual return type is %r" % (op, FUNC, RESULT))
        # ok
        # get the 'elidable' and 'loopinvariant' flags from the function object
        elidable = False
        loopinvariant = False
        call_release_gil_target = llmemory.NULL
        if op.opname == "direct_call":
            funcobj = op.args[0].value._obj
            assert getattr(funcobj, 'calling_conv', 'c') == 'c', (
                "%r: getcalldescr() with a non-default call ABI" % (op,))
            func = getattr(funcobj, '_callable', None)
            elidable = getattr(func, "_elidable_function_", False)
            loopinvariant = getattr(func, "_jit_loop_invariant_", False)
            if loopinvariant:
                assert not NON_VOID_ARGS, ("arguments not supported for "
                                           "loop-invariant function!")
            if getattr(func, "_call_aroundstate_target_", None):
                call_release_gil_target = func._call_aroundstate_target_
                call_release_gil_target = llmemory.cast_ptr_to_adr(
                    call_release_gil_target)
        # build the extraeffect
        random_effects = self.randomeffects_analyzer.analyze(op)
        if random_effects:
            extraeffect = EffectInfo.EF_RANDOM_EFFECTS
        # random_effects implies can_invalidate
        can_invalidate = random_effects or self.quasiimmut_analyzer.analyze(op)
        if extraeffect is None:
            if self.virtualizable_analyzer.analyze(op):
                extraeffect = EffectInfo.EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE
            elif loopinvariant:
                extraeffect = EffectInfo.EF_LOOPINVARIANT
            elif elidable:
                if self._canraise(op):
                    extraeffect = EffectInfo.EF_ELIDABLE_CAN_RAISE
                else:
                    extraeffect = EffectInfo.EF_ELIDABLE_CANNOT_RAISE
            elif self._canraise(op):
                extraeffect = EffectInfo.EF_CAN_RAISE
            else:
                extraeffect = EffectInfo.EF_CANNOT_RAISE
        #
        # check that the result is really as expected
        if loopinvariant:
            if extraeffect != EffectInfo.EF_LOOPINVARIANT:
                from rpython.jit.codewriter.policy import log; log.WARNING(
                "in operation %r: this calls a _jit_loop_invariant_ function,"
                " but this contradicts other sources (e.g. it can have random"
                " effects): EF=%s" % (op, extraeffect))
        if elidable:
            if extraeffect not in (EffectInfo.EF_ELIDABLE_CANNOT_RAISE,
                                   EffectInfo.EF_ELIDABLE_CAN_RAISE):
                from rpython.jit.codewriter.policy import log; log.WARNING(
                "in operation %r: this calls an _elidable_function_,"
                " but this contradicts other sources (e.g. it can have random"
                " effects): EF=%s" % (op, extraeffect))
        #
        effectinfo = effectinfo_from_writeanalyze(
            self.readwrite_analyzer.analyze(op, self.seen), self.cpu,
            extraeffect, oopspecindex, can_invalidate, call_release_gil_target,
        )
        #
        assert effectinfo is not None
        if elidable or loopinvariant:
            assert extraeffect != EffectInfo.EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE
            # XXX this should also say assert not can_invalidate, but
            #     it can't because our analyzer is not good enough for now
            #     (and getexecutioncontext() can't really invalidate)
        #
        return self.cpu.calldescrof(FUNC, tuple(NON_VOID_ARGS), RESULT,
                                    effectinfo)

    def _canraise(self, op):
        if op.opname == 'pseudo_call_cannot_raise':
            return False
        try:
            return self.raise_analyzer.can_raise(op)
        except lltype.DelayedPointer:
            return True  # if we need to look into the delayed ptr that is
                         # the portal, then it's certainly going to raise

    def calldescr_canraise(self, calldescr):
        effectinfo = calldescr.get_extra_info()
        return effectinfo.check_can_raise()

    def jitdriver_sd_from_portal_graph(self, graph):
        for jd in self.jitdrivers_sd:
            if jd.portal_graph is graph:
                return jd
        return None

    def jitdriver_sd_from_portal_runner_ptr(self, funcptr):
        for jd in self.jitdrivers_sd:
            if funcptr is jd.portal_runner_ptr:
                return jd
        return None

    def jitdriver_sd_from_jitdriver(self, jitdriver):
        for jd in self.jitdrivers_sd:
            if jd.jitdriver is jitdriver:
                return jd
        return None

    def get_vinfo(self, VTYPEPTR):
        seen = set()
        for jd in self.jitdrivers_sd:
            if jd.virtualizable_info is not None:
                if jd.virtualizable_info.is_vtypeptr(VTYPEPTR):
                    seen.add(jd.virtualizable_info)
        if seen:
            assert len(seen) == 1
            return seen.pop()
        else:
            return None

    def could_be_green_field(self, GTYPE, fieldname):
        GTYPE_fieldname = (GTYPE, fieldname)
        for jd in self.jitdrivers_sd:
            if jd.greenfield_info is not None:
                if GTYPE_fieldname in jd.greenfield_info.green_fields:
                    return True
        return False
