from pypy.annotation import policy
from pypy.annotation.specialize import getuniquenondirectgraph
from pypy.translator.translator import graphof

class HintAnnotatorPolicy(policy.AnnotatorPolicy):
    novirtualcontainer     = False
    oopspec                = False
    entrypoint_returns_red = True

    def __init__(self, novirtualcontainer     = None,
                       oopspec                = None,
                       entrypoint_returns_red = None):
        if novirtualcontainer is not None:
            self.novirtualcontainer = novirtualcontainer
        if oopspec is not None:
            self.oopspec = oopspec
        if entrypoint_returns_red is not None:
            self.entrypoint_returns_red = entrypoint_returns_red

    def look_inside_graph(self, graph):
        return True


class StopAtXPolicy(HintAnnotatorPolicy):
    """Useful for tests."""
    novirtualcontainer = True
    oopspec = True

    def __init__(self, *funcs):
        self.funcs = funcs

    def look_inside_graph(self, graph):
        try:
            if graph.func in self.funcs:
                return False
        except AttributeError:
            pass
        return True

class ManualGraphPolicy(HintAnnotatorPolicy):
    novirtualcontainer = True
    oopspec = True
    opaquepurefunctions = False

    def seetranslator(self, t):
        if self.opaquepurefunctions:
            from pypy.jit.hintannotator.bookkeeper import ImpurityAnalyzer
            self.analyzer = ImpurityAnalyzer(t)
        self.translator = t
        self.bookkeeper = t.annotator.bookkeeper
        self.timeshift_graphs = {}
        portal = getattr(self.PORTAL, 'im_func', self.PORTAL)
        portal_graph = graphof(t, portal)
        self.fill_timeshift_graphs(portal_graph)

    def look_inside_graph(self, graph):
        if graph in self.timeshift_graphs:
            return self.timeshift_graphs[graph]
        # don't look into pure functions
        if (self.opaquepurefunctions and
            not self.analyzer.analyze_direct_call(graph)):
            return False
        try:
            func = graph.func
        except AttributeError:
            return True
        if hasattr(func, '_look_inside_me_'):
            return func._look_inside_me_
        # explicitly pure functions are always opaque
        if getattr(func, '_pure_function_', False):
            return False
        mod = func.__module__ or '?'
        return self.look_inside_graph_of_module(graph, func, mod)

    def look_inside_graph_of_module(self, graph, func, mod):
        return True

    def fill_timeshift_graphs(self, portal_graph):
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
                                       targetgraphs)
        for graph in graphs:
            self.timeshift_graphs[graph] = True

    def seepath(self, *path):
        for i in range(1, len(path)):
            self.seefunc(path[i-1], path[i])

    def seegraph(self, func, look=True):
        graph = self._graph(func)
        self.timeshift_graphs[graph] = look



def enumerate_reachable_graphs(translator, startgraph):
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
            for block, callee in find_calls_from(translator, head):
                if callee not in seen:
                    newnode = callee, node
                    yield newnode
                    nextlengthlist.append(newnode)
                    nextseen[callee] = True
        pending = nextlengthlist
        seen.update(nextseen)
    yield None

def graphs_on_the_path_to(translator, startgraph, targetgraphs):
    targetgraphs = targetgraphs.copy()
    result = {}
    found = {}
    for node in enumerate_reachable_graphs(translator, startgraph):
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


