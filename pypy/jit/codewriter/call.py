#
# Contains the logic to decide, based on the policy, which graphs
# to transform to JitCodes or not.
#

from pypy.jit.codewriter import support
from pypy.jit.codewriter.jitcode import JitCode
from pypy.jit.codewriter.effectinfo import VirtualizableAnalyzer
from pypy.jit.codewriter.effectinfo import QuasiImmutAnalyzer
from pypy.jit.codewriter.effectinfo import effectinfo_from_writeanalyze
from pypy.jit.codewriter.effectinfo import EffectInfo, CallInfoCollection
from pypy.translator.simplify import get_funcobj, get_functype
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.translator.backendopt.canraise import RaiseAnalyzer
from pypy.translator.backendopt.writeanalyze import ReadWriteAnalyzer


class CallControl(object):
    virtualref_info = None     # optionally set from outside

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
        #
        for index, jd in enumerate(jitdrivers_sd):
            jd.index = index

    def find_all_graphs(self, policy):
        try:
            return self.candidate_graphs
        except AttributeError:
            pass

        def is_candidate(graph):
            return policy.look_inside_graph(graph)

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
                if op.opname not in ("direct_call", "indirect_call", "oosend"):
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
            funcobj = get_funcobj(op.args[0].value)
            graph = funcobj.graph
            if is_candidate(graph):
                return [graph]     # common case: look inside this graph
        else:
            assert op.opname in ('indirect_call', 'oosend')
            if op.opname == 'indirect_call':
                graphs = op.args[-1].value
            else:
                v_obj = op.args[1].concretetype
                graphs = v_obj._lookup_graphs(op.args[0].value)
            #
            if graphs is None:
                # special case: handle the indirect call that goes to
                # the 'instantiate' methods.  This check is a bit imprecise
                # but it's not too bad if we mistake a random indirect call
                # for the one to 'instantiate'.
                from pypy.rpython.lltypesystem import rclass
                CALLTYPE = op.args[0].concretetype
                if (op.opname == 'indirect_call' and len(op.args) == 2 and
                    CALLTYPE == rclass.OBJECT_VTABLE.instantiate):
                    graphs = list(self._graphs_of_all_instantiate())
            #
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

    def _graphs_of_all_instantiate(self):
        for vtable in self.rtyper.lltype2vtable.values():
            if vtable.instantiate:
                yield vtable.instantiate._obj.graph

    def guess_call_kind(self, op, is_candidate=None):
        if op.opname == 'direct_call':
            funcptr = op.args[0].value
            if self.jitdriver_sd_from_portal_runner_ptr(funcptr) is not None:
                return 'recursive'
            funcobj = get_funcobj(funcptr)
            if getattr(funcobj, 'graph', None) is None:
                return 'residual'
            targetgraph = funcobj.graph
            if (hasattr(targetgraph, 'func') and
                hasattr(targetgraph.func, 'oopspec')):
                return 'builtin'
        elif op.opname == 'oosend':
            SELFTYPE, methname, opargs = support.decompose_oosend(op)
            if SELFTYPE.oopspec_name is not None:
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
        FUNC = get_functype(lltype.typeOf(fnptr))
        assert lltype.Ptr(lltype.PyObject) not in FUNC.ARGS
        if self.rtyper.type_system.name == 'ootypesystem':
            XXX
        else:
            fnaddr = llmemory.cast_ptr_to_adr(fnptr)
        NON_VOID_ARGS = [ARG for ARG in FUNC.ARGS if ARG is not lltype.Void]
        calldescr = self.cpu.calldescrof(FUNC, tuple(NON_VOID_ARGS),
                                         FUNC.RESULT)
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
        FUNC = get_functype(op.args[0].concretetype)
        ARGS = FUNC.ARGS
        assert NON_VOID_ARGS == [T for T in ARGS if T is not lltype.Void]
        assert RESULT == FUNC.RESULT
        # ok
        # get the 'pure' and 'loopinvariant' flags from the function object
        pure = False
        loopinvariant = False
        if op.opname == "direct_call":
            func = getattr(get_funcobj(op.args[0].value), '_callable', None)
            pure = getattr(func, "_pure_function_", False)
            loopinvariant = getattr(func, "_jit_loop_invariant_", False)
            if loopinvariant:
                assert not NON_VOID_ARGS, ("arguments not supported for "
                                           "loop-invariant function!")
        # build the extraeffect
        if extraeffect is None:
            if self.virtualizable_analyzer.analyze(op):
                extraeffect = EffectInfo.EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE
            elif self.quasiimmut_analyzer.analyze(op):
                extraeffect = EffectInfo.EF_CAN_INVALIDATE
            elif loopinvariant:
                extraeffect = EffectInfo.EF_LOOPINVARIANT
            elif pure:
                # XXX check what to do about exceptions (also MemoryError?)
                extraeffect = EffectInfo.EF_PURE
            elif self._canraise(op):
                extraeffect = EffectInfo.EF_CAN_RAISE
            else:
                extraeffect = EffectInfo.EF_CANNOT_RAISE
        #
        effectinfo = effectinfo_from_writeanalyze(
            self.readwrite_analyzer.analyze(op), self.cpu, extraeffect,
            oopspecindex)
        #
        if oopspecindex != EffectInfo.OS_NONE:
            assert effectinfo is not None
        if pure or loopinvariant:
            assert effectinfo is not None
            assert extraeffect != EffectInfo.EF_FORCES_VIRTUAL_OR_VIRTUALIZABLE
            assert extraeffect != EffectInfo.EF_CAN_INVALIDATE
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
        return (effectinfo is None or
                effectinfo.extraeffect >= EffectInfo.EF_CAN_RAISE)

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
