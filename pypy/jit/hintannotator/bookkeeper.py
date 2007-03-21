import py
from pypy.tool.tls import tlsobject
from pypy.tool.ansi_print import ansi_log
from pypy.rlib import objectmodel
from pypy.objspace.flow.model import copygraph, SpaceOperation, Constant
from pypy.objspace.flow.model import Variable, Block, Link, FunctionGraph
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem import lltype, lloperation
from pypy.tool.algo.unionfind import UnionFind
from pypy.translator.backendopt import graphanalyze
from pypy.translator.unsimplify import copyvar

TLS = tlsobject()

log = py.log.Producer("hintannotate")
py.log.setconsumer("hintannotate", ansi_log)

TIMESHIFTMAP = {Constant(objectmodel._we_are_jitted):
                Constant(1, lltype.Signed)}

class GraphDesc(object):

    def __init__(self, bookkeeper, origgraph):
        self.bookkeeper = bookkeeper
        self.origgraph = origgraph
        self._cache = {}

    def specialize(self, input_args_hs, key=None, alt_name=None):
        # get the specialized graph -- for now, no specialization
        graph = self.cachedgraph(key, alt_name)

        # modify input_args_hs in-place to change their origin
        for i in range(len(input_args_hs)):
            hs_v1 = input_args_hs[i]
            if isinstance(hs_v1, hintmodel.SomeLLAbstractConstant):
                myorigin = self.bookkeeper.myinputargorigin(graph, i)
                hs_v1 = hintmodel.SomeLLAbstractConstant(
                    hs_v1.concretetype, {myorigin: True},
                    eager_concrete = hs_v1.eager_concrete,
                    deepfrozen     = hs_v1.deepfrozen,
                    myorigin       = myorigin)
                input_args_hs[i] = hs_v1
        return graph

    def cachedgraph(self, key, alt_name=None):
        verbose = self.bookkeeper.annotator.translator.config.translation.verbose
        try:
            return self._cache[key]
        except KeyError:
            bk = self.bookkeeper
            look = bk.annotator.policy.look_inside_graph(self.origgraph)
            if look:
                if callable(look):
                    graph = self.build_metacall_graph(self.origgraph, look)
                else:
                    # normal case
                    graph = copygraph(self.origgraph, varmap=TIMESHIFTMAP)
                if not self._cache:
                    bk.nonstuboriggraphcount += 1
                if verbose:
                    log(str(graph))
                else:
                    log.dot()
            else:
                graph = self.build_callback_graph(self.origgraph)
                if not self._cache:
                    bk.stuboriggraphcount += 1                
                if verbose:
                    log.stub(str(graph))
                else:
                    log.dot()
            graph.tag = 'timeshifted'
            try:
                etrafo = bk.annotator.exceptiontransformer
            except AttributeError:
                pass
            else:
                # except transform the copied graph before its hint-annotation
                etrafo.create_exception_handling(graph, always_exc_clear=True)
            if alt_name is not None:
                graph.name = alt_name
            self._cache[key] = graph
            self.bookkeeper.annotator.translator.graphs.append(graph)
            return graph

    def build_callback_graph(self, graph):
        args_v = [copyvar(None, v) for v in graph.getargs()]
        v_res = copyvar(None, graph.getreturnvar())
        rtyper = self.bookkeeper.annotator.base_translator.rtyper  # fish
        fnptr = rtyper.getcallable(graph)
        v_ptr = Constant(fnptr, lltype.typeOf(fnptr))
        newstartblock = Block(args_v)
        newstartblock.operations.append(
            SpaceOperation('direct_call', [v_ptr] + args_v, v_res))
        newgraph = FunctionGraph('%s_ts_stub' % (graph.name,), newstartblock)
        newgraph.getreturnvar().concretetype = v_res.concretetype
        newstartblock.closeblock(Link([v_res], newgraph.returnblock))
        return newgraph

    def build_metacall_graph(self, origgraph, metadesccls):
        args_v = [copyvar(None, v) for v in origgraph.getargs()]
        v_res = copyvar(None, origgraph.getreturnvar())
        v_metadesccls = Constant(metadesccls, lltype.Void)
        newstartblock = Block(args_v)
        newstartblock.operations.append(
            SpaceOperation('ts_metacall', [v_metadesccls] + args_v, v_res))
        newgraph = FunctionGraph('%s_ts_metacall' % (origgraph.name,),
                                 newstartblock)
        newgraph.getreturnvar().concretetype = v_res.concretetype
        newstartblock.closeblock(Link([v_res], newgraph.returnblock))
        return newgraph


class TsGraphCallFamily:
    def __init__(self, tsgraph):
        self.tsgraphs = {tsgraph: True}

    def update(self, other):
        self.tsgraphs.update(other.tsgraphs)


class ImpurityAnalyzer(graphanalyze.GraphAnalyzer):
    """An impure graph has side-effects or depends on state that
    can be mutated.  A pure graph always gives the same answer for
    given arguments."""

    def analyze_exceptblock(self, block, seen=None):
        return True      # for now, we simplify and say that functions
                         # raising exceptions cannot be pure

    def operation_is_true(self, op):
        operation = lloperation.LL_OPERATIONS[op.opname]
        ARGTYPES = [v.concretetype for v in op.args]
        return not operation.is_pure(*ARGTYPES)


class HintBookkeeper(object):

    def __init__(self, hannotator):
        self.pending_specializations = []
        self.originflags = {}
        self.virtual_containers = {}
        self.descs = {}
        self.tsgraph_maximal_call_families = UnionFind(TsGraphCallFamily)
        self.annotator = hannotator
        self.tsgraphsigs = {}
        self.nonstuboriggraphcount = 0
        self.stuboriggraphcount = 0
        if hannotator is not None:     # for tests
            t = hannotator.base_translator
            self.impurity_analyzer = ImpurityAnalyzer(t)
        # circular imports hack
        global hintmodel
        from pypy.jit.hintannotator import model as hintmodel

    def getdesc(self, graph):
        try:
            return self.descs[graph]
        except KeyError:
            self.descs[graph] = desc = GraphDesc(self, graph)
            return desc

    def enter(self, position_key):
        """Start of an operation.
        The operation is uniquely identified by the given key."""
        res = getattr(self, 'position_key', None)
        self.position_key = position_key
        TLS.bookkeeper = self
        return res

    def leave(self, old=None):
        """End of an operation."""
        if old is None:
            del TLS.bookkeeper
            del self.position_key
        else:
            self.position_key = old

    def myinputargorigin(self, graph, i):
        try:
            origin = self.originflags[graph, i]
        except KeyError:
            origin = hintmodel.InputArgOriginFlags(self, graph, i)
            self.originflags[graph, i] = origin
        return origin

    def myorigin(self):
        try:
            origin = self.originflags[self.position_key]
        except KeyError:
            assert len(self.position_key) == 3
            graph, block, i = self.position_key
            spaceop = block.operations[i]
            spaceop = SpaceOperation(spaceop.opname,
                                     list(spaceop.args),
                                     spaceop.result)
            origin = hintmodel.OriginFlags(self, spaceop)
            self.originflags[self.position_key] = origin
        return origin

    def compute_at_fixpoint(self):
        binding = self.annotator.binding

        # for the entry point, we need to remove the 'myorigin' of
        # the input arguments (otherwise they will always be green,
        # as there is no call to the entry point to make them red)
        tsgraph = self.annotator.translator.graphs[0]
        for v in tsgraph.getargs():
            hs_arg = binding(v)
            if isinstance(hs_arg, hintmodel.SomeLLAbstractConstant):
                hs_arg.myorigin = None
        # for convenience, force the return var to be red too, as
        # the timeshifter doesn't support anything else
        if self.annotator.policy.entrypoint_returns_red:
            v = tsgraph.getreturnvar()
            hs_red = hintmodel.variableoftype(v.concretetype)
            self.annotator.setbinding(v, hs_red)

        # propagate the green/red constraints
        log.event("Computing maximal green set...")
        greenorigindependencies = {}
        callreturndependencies = {}
        for origin in self.originflags.values():
            origin.greenargs = True
            origin.record_dependencies(greenorigindependencies,
                                       callreturndependencies)

        while True:
            progress = False
            # check all calls to see if they are green calls or not
            for origin, graphs in callreturndependencies.items():
                if self.is_green_call(origin.spaceop):
                    pass   # green call => don't force spaceop.result to red
                else:
                    # non-green calls: replace the dependency with a regular
                    # dependency from graph.getreturnvar() to spaceop.result
                    del callreturndependencies[origin]
                    retdeps = greenorigindependencies.setdefault(origin, [])
                    for graph in graphs:
                        retdeps.append(graph.getreturnvar())
            # propagate normal dependencies
            for origin, deps in greenorigindependencies.items():
                for v in deps:
                    if not binding(v).is_green():
                        # not green => force the origin to be red too
                        origin.greenargs = False
                        del greenorigindependencies[origin]
                        progress = True
                        break
            if not progress:
                break

        for callfamily in self.tsgraph_maximal_call_families.infos():
            if len(callfamily.tsgraphs) > 1:
                # if at least one graph in the family returns a red,
                # we force a red as the return of all of them
                returns_red = False
                for graph in callfamily.tsgraphs:
                    if not binding(graph.getreturnvar()).is_green():
                        returns_red = True
                if returns_red:
                    for graph in callfamily.tsgraphs:
                        v = graph.getreturnvar()
                        hs_red = hintmodel.variableoftype(v.concretetype)
                        self.annotator.setbinding(v, hs_red)

        # compute and cache the signature of the graphs before they are
        # modified by further code
        ha = self.annotator
        for tsgraph in ha.translator.graphs:
            sig_hs = ([ha.binding(v) for v in tsgraph.getargs()],
                      ha.binding(tsgraph.getreturnvar()))
            self.tsgraphsigs[tsgraph] = sig_hs

    def is_pure_graph(self, graph):
        impure = self.impurity_analyzer.analyze_direct_call(graph)
        return not impure

    def is_green_call(self, callop):
        "Is the given call operation completely computable at compile-time?"
        for v in callop.args:
            hs_arg = self.annotator.binding(v)
            if not hs_arg.is_green():
                return False
        # all-green arguments.  Note that we can return True even if the
        # result appears to be red; it's not a real red result then.
        impure = self.impurity_analyzer.analyze(callop)
        return not impure

    def immutableconstant(self, const):
        res = hintmodel.SomeLLAbstractConstant(const.concretetype, {})
        res.const = const.value
        # we want null pointers to be deepfrozen!
        if isinstance(const.concretetype, lltype.Ptr):
            if not const.value:
                res.deepfrozen = True
        return res

    def immutablevalue(self, value):
        return self.immutableconstant(Constant(value, lltype.typeOf(value)))

    def current_op_concretetype(self):
        _, block, i = self.position_key
        op = block.operations[i]
        return op.result.concretetype

    def current_op_binding(self):
        _, block, i = self.position_key
        op = block.operations[i]
        hs_res = self.annotator.binding(op.result, annmodel.s_ImpossibleValue)
        return hs_res

    def getvirtualcontainerdef(self, TYPE, constructor=None):
        try:
            res = self.virtual_containers[self.position_key]
            assert res.T == TYPE
        except KeyError:
            if constructor is None:
                from pypy.jit.hintannotator.container import virtualcontainerdef
                constructor = virtualcontainerdef
            res = constructor(self, TYPE)
            self.virtual_containers[self.position_key] = res
        return res

    def warning(self, msg):
        return self.annotator.warning(msg)

    def specialization_key(self, fixed, args_hs):
        if fixed:
            return 'fixed'
        else:
            key = []
            specialize = False
            for i, arg_hs in enumerate(args_hs):
                if isinstance(arg_hs, hintmodel.SomeLLAbstractVariable):
                    key.append('v')
                    specialize = True
                    continue

                if (isinstance(arg_hs, hintmodel.SomeLLAbstractConstant)
                    and arg_hs.eager_concrete):
                    key.append('E')
                    specialize = True
                else:
                    key.append('x')

                if (isinstance(arg_hs, hintmodel.SomeLLAbstractConstant)
                    and arg_hs.deepfrozen):
                    key.append('D')
                    specialize = True
                else:
                    key.append('x')

            if specialize:
                return ''.join(key)
            else:
                return None

    def get_graph_by_key(self, graph, specialization_key):
        desc = self.getdesc(graph)
        return desc._cache[specialization_key]

    def get_graph_for_call(self, graph, fixed, args_hs):
        # this can modify args_hs in-place!
        key = self.specialization_key(fixed, args_hs)
        if key is None:
            alt_name = None
        else:
            alt_name = graph.name + '_H'+key
        desc = self.getdesc(graph)
        graph = desc.specialize(args_hs, key=key, alt_name=alt_name)
        return graph

    def graph_call(self, graph, fixed, args_hs,
                   tsgraph_accum=None, hs_callable=None):
        input_args_hs = list(args_hs)
        graph = self.get_graph_for_call(graph, fixed, input_args_hs)
        if tsgraph_accum is not None:
            tsgraph_accum.append(graph)     # save this if the caller cares

        # propagate fixing of arguments in the function to the caller
        for inp_arg_hs, arg_hs in zip(input_args_hs, args_hs):
            if isinstance(arg_hs, hintmodel.SomeLLAbstractConstant):
                assert len(inp_arg_hs.origins) == 1
                [o] = inp_arg_hs.origins.keys()
                if o.read_fixed():
                    for o in arg_hs.origins:
                        o.set_fixed()
        
        hs_res = self.annotator.recursivecall(graph,
                                              self.position_key,
                                              input_args_hs)
        # look on which input args the hs_res result depends on
        if isinstance(hs_res, hintmodel.SomeLLAbstractConstant):
            if (hs_callable is not None and
                not isinstance(hs_callable, hintmodel.SomeLLAbstractConstant)):
                hs_res = hintmodel.variableoftype(hs_res.concretetype,
                                                  hs_res.deepfrozen)
            else:
                deps_hs = []
                for hs_inputarg, hs_arg in zip(input_args_hs, args_hs):
                    if isinstance(hs_inputarg,
                                  hintmodel.SomeLLAbstractConstant):
                        assert len(hs_inputarg.origins) == 1
                        [o] = hs_inputarg.origins.keys()
                        if o in hs_res.origins:
                            deps_hs.append(hs_arg)
                if fixed:
                    deps_hs.append(hs_res)
                hs_res = hintmodel.reorigin(hs_res, hs_callable, *deps_hs)
        return hs_res

    def graph_family_call(self, graph_list, fixed, args_hs,
                          tsgraphs_accum=None, hs_callable=None):
        if tsgraphs_accum is None:
            tsgraphs = []
        else:
            tsgraphs = tsgraphs_accum
        results_hs = []
        for graph in graph_list:
            results_hs.append(self.graph_call(graph, fixed, args_hs,
                                              tsgraphs, hs_callable))
        # put the tsgraphs in the same call family
        call_families = self.tsgraph_maximal_call_families
        _, rep, callfamily = call_families.find(tsgraphs[0])
        for tsgraph in tsgraphs[1:]:
            _, rep, callfamily = call_families.union(rep, tsgraph)
        return annmodel.unionof(*results_hs)

# get current bookkeeper

def getbookkeeper():
    """Get the current Bookkeeper.
    Only works during the analysis of an operation."""
    try:
        return TLS.bookkeeper
    except AttributeError:
        return None
