
class JitPolicy(object):

    def look_inside_function(self, func):
        if hasattr(func, '_look_inside_me_'):
            return func._look_inside_me_
        # explicitly pure functions are always opaque
        if getattr(func, '_pure_function_', False):
            return False
        # pypy.rpython.module.* are opaque helpers
        mod = func.__module__ or '?'
        if mod.startswith('pypy.rpython.module.'):
            return False
        return True

    def look_inside_graph(self, graph):
        try:
            func = graph.func
        except AttributeError:
            return True
        return self.look_inside_function(func)

    def graphs_from(self, op):
        if op.opname == 'direct_call':
            graph = op.args[0].value._obj.graph
            if self.look_inside_graph(graph):
                return [graph]     # common case: look inside this graph
        else:
            assert op.opname == 'indirect_call'
            graphs = op.args[-1].value
            for graph in graphs:
                if self.look_inside_graph(graph):
                    return graphs  # common case: look inside at least 1 graph
        # residual call case: we don't need to look into any graph
        return None

    def guess_call_kind(self, op):
        if op.opname == 'direct_call':
            if getattr(op.args[0].value._obj, 'graph', None):
                return 'builtin'
            targetgraph = op.args[0].value._obj.graph
            if (hasattr(targetgraph, 'func') and
                hasattr(targetgraph.func, 'oopspec')):
                return 'builtin'
        if self.graphs_from(op) is None:
            return 'residual'
        return 'regular'


class StopAtXPolicy(JitPolicy):
    def __init__(self, *funcs):
        self.funcs = funcs

    def look_inside_function(self, func):
        if func in self.funcs:
            return False
        return super(StopAtXPolicy, self).look_inside_function(func)

# ____________________________________________________________

from pypy.annotation.specialize import getuniquenondirectgraph

class ManualJitPolicy(JitPolicy):
    def __init__(self, translator):
        self.translator = translator
        self.bookkeeper = translator.annotator.bookkeeper
        self.enabled_graphs = {}
        self.memo = {}
        self.fill_seen_graphs()

    def look_inside_graph(self, graph):
        if graph in self.enabled_graphs:
            return self.enabled_graphs[graph]
        return super(ManualJitPolicy, self).look_inside_graph(graph)

    def fill_seen_graphs(self):
        # subclasses should have their own
        pass

    def _graph(self, func):
        func = getattr(func, 'im_func', func)
        desc = self.bookkeeper.getdesc(func)
        return getuniquenondirectgraph(desc)

    def seefunc(self, fromfunc, *tofuncs):
        targetgraphs = {}
        for tofunc in tofuncs:
            targetgraphs[self._graph(tofunc)] = True
        graphs = graphs_on_the_path_to(self.translator, self._graph(fromfunc),
                                       targetgraphs, self.memo)
        for graph in graphs:
            if graph not in self.enabled_graphs:
                self.enabled_graphs[graph] = True
                print '++', graph

    def seepath(self, *path):
        assert len(path) >= 2
        for i in range(1, len(path)):
            self.seefunc(path[i-1], path[i])

    def seegraph(self, func, look=True):
        graph = self._graph(func)
        self.enabled_graphs[graph] = look
        if look:
            print '++', graph
        else:
            print '--', graph

def enumerate_reachable_graphs(translator, startgraph, memo=None):
    from pypy.translator.backendopt.support import find_calls_from
    pending = [(startgraph, None)]
    yield pending[0]
    seen = {startgraph: True}
    while pending:
        yield None     # hack: a separator meaning "length increases now"
        nextlengthlist = []
        nextseen = {}
        for node in pending:
            head, tail = node
            for block, callee in find_calls_from(translator, head, memo):
                if callee not in seen:
                    newnode = callee, node
                    yield newnode
                    nextlengthlist.append(newnode)
                    nextseen[callee] = True
        pending = nextlengthlist
        seen.update(nextseen)
    yield None

def graphs_on_the_path_to(translator, startgraph, targetgraphs, memo=None):
    targetgraphs = targetgraphs.copy()
    result = {}
    found = {}
    for node in enumerate_reachable_graphs(translator, startgraph, memo):
        if node is None:  # hack: a separator meaning "length increases now"
            for graph in found:
                del targetgraphs[graph]
            found.clear()
            if not targetgraphs:
                return result
        elif node[0] in targetgraphs:
            found[node[0]] = True
            while node is not None:
                head, tail = node
                result[head] = True
                node = tail
    raise Exception("did not reach all targets:\nmissing %r" % (
        targetgraphs.keys(),))
