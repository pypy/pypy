from pypy.tool.tls import tlsobject
from pypy.objspace.flow.model import copygraph
from pypy.annotation import model as annmodel

TLS = tlsobject()


class GraphDesc(object):

    def __init__(self, bookkeeper, origgraph):
        self.bookkeeper = bookkeeper
        self.origgraph = origgraph
        self._cache = {}

    def specialize(self, input_args_hs, key=None, alt_name=None):
        from pypy.jit.hintannotator import model as hintmodel
        # get the specialized graph -- for now, no specialization
        graph = self.cachedgraph(key, alt_name)

        # modify input_args_hs in-place to change their origin
        for i in range(len(input_args_hs)):
            old = self.bookkeeper.enter((graph, i))
            try:
                input_args_hs[i] = hintmodel.reorigin(input_args_hs[i])
            finally:
                self.bookkeeper.leave(old)

        return graph

    def cachedgraph(self, key, alt_name=None):
        try:
            return self._cache[key]
        except KeyError:
            graph = copygraph(self.origgraph)
            if alt_name is not None:
                graph.name = alt_name
            self._cache[key] = graph
            self.bookkeeper.annotator.translator.graphs.append(graph)
            return graph


class HintBookkeeper(object):

    def __init__(self, hannotator):
        self.pending_specializations = []
        self.originflags = {}
        self.virtual_containers = {}
        self.descs = {}
        self.annotator = hannotator

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

    def myorigin(self):
        try:
            origin = self.originflags[self.position_key]
        except KeyError:
            from pypy.jit.hintannotator import model as hintmodel
            origin = hintmodel.OriginFlags()
            self.originflags[self.position_key] = origin
        return origin

    def compute_at_fixpoint(self):
        pass

    def immutableconstant(self, const):
        from pypy.jit.hintannotator import model as hintmodel
        res = hintmodel.SomeLLAbstractConstant(const.concretetype, {})
        res.const = const.value
        return res

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

    def get_graph_for_call(self, graph, fixed, args_hs):
        # this can modify args_hs in-place!
        from pypy.jit.hintannotator.model import SomeLLAbstractConstant
        desc = self.getdesc(graph)
        key = None
        alt_name = None
        if fixed:
            key = 'fixed'
            alt_name = graph.name + '_HFixed'
        else:
            key = []
            specialize = False
            for i, arg_hs in enumerate(args_hs):
                if isinstance(arg_hs, SomeLLAbstractConstant) and arg_hs.eager_concrete:
                    key.append('E')
                    specialize = True
                else:
                    key.append('x')
            if specialize:
                key = ''.join(key)
                alt_name = graph.name + '_H'+key
            else:
                key = None

        graph = desc.specialize(args_hs, key=key, alt_name=alt_name)
        return graph

# get current bookkeeper

def getbookkeeper():
    """Get the current Bookkeeper.
    Only works during the analysis of an operation."""
    try:
        return TLS.bookkeeper
    except AttributeError:
        return None
