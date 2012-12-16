from pypy.translator.simplify import get_graph, get_funcobj
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.rpython.lltypesystem import lltype

class GraphAnalyzer(object):
    verbose = False

    def __init__(self, translator):
        self.translator = translator
        self._analyzed_calls = {}

    # method overridden by subclasses

    @staticmethod
    def join_two_results(result1, result2):
        raise NotImplementedError("abstract base class")

    @staticmethod
    def bottom_result():
        raise NotImplementedError("abstract base class")

    @staticmethod
    def top_result():
        raise NotImplementedError("abstract base class")

    @staticmethod
    def is_top_result(result):
        # only an optimization, safe to always return False
        return False

    def analyze_simple_operation(self, op, graphinfo=None):
        raise NotImplementedError("abstract base class")

    # some sensible default methods, can also be overridden

    def analyze_exceptblock(self, block, seen=None):
        return self.bottom_result()

    def analyze_startblock(self, block, seen=None):
        return self.bottom_result()

    def analyze_external_call(self, op, seen=None):
        funcobj = get_funcobj(op.args[0].value)
        result = self.bottom_result()
        if hasattr(funcobj, '_callbacks'):
            bk = self.translator.annotator.bookkeeper
            for function in funcobj._callbacks.callbacks:
                desc = bk.getdesc(function)
                for graph in desc.getgraphs():
                    result = self.join_two_results(
                        result, self.analyze_direct_call(graph, seen))
        return result

    def analyze_external_method(self, op, TYPE, meth):
        return self.top_result()

    def analyze_link(self, graph, link):
        return self.bottom_result()

    # general methods

    def join_results(self, results):
        result = self.bottom_result()
        for sub in results:
            result = self.join_two_results(result, sub)
        return result

    def compute_graph_info(self, graph):
        return None

    def analyze(self, op, seen=None, graphinfo=None):
        if op.opname == "direct_call":
            graph = get_graph(op.args[0], self.translator)
            if graph is None:
                x = self.analyze_external_call(op, seen)
                if self.verbose and x:
                    print '\tanalyze_external_call %s: %r' % (op, x)
                return x
            x = self.analyze_direct_call(graph, seen)
            if self.verbose and x:
                print '\tanalyze_direct_call(%s): %r' % (graph, x)
            return x
        elif op.opname == "indirect_call":
            graphs = op.args[-1].value
            if graphs is None:
                if self.verbose:
                    print '\t%s to unknown' % (op,)
                return self.top_result()
            x = self.analyze_indirect_call(graphs, seen)
            if self.verbose and x:
                print '\tanalyze_indirect_call(%s): %r' % (graphs, x)
            return x
        elif op.opname == "oosend":
            name = op.args[0].value
            TYPE = op.args[1].concretetype
            _, meth = TYPE._lookup(name)
            graph = getattr(meth, 'graph', None)
            if graph is None:
                return self.analyze_external_method(op, TYPE, meth)
            return self.analyze_oosend(TYPE, name, seen)
        x = self.analyze_simple_operation(op, graphinfo)
        if self.verbose and x:
            print '\t%s: %r' % (op, x)
        return x

    def analyze_direct_call(self, graph, seen=None):
        if seen is None:
            seen = DependencyTracker(self)
        if not seen.enter(graph):
            return seen.get_cached_result(graph)
        result = self.bottom_result()
        graphinfo = self.compute_graph_info(graph)
        for block in graph.iterblocks():
            if block is graph.startblock:
                result = self.join_two_results(
                        result, self.analyze_startblock(block, seen))
            elif block is graph.exceptblock:
                result = self.join_two_results(
                        result, self.analyze_exceptblock(block, seen))
            for op in block.operations:
                result = self.join_two_results(
                        result, self.analyze(op, seen, graphinfo))
            for exit in block.exits:
                result = self.join_two_results(
                        result, self.analyze_link(exit, seen))
            if self.is_top_result(result):
                break
        seen.leave_with(result)
        return result

    def analyze_indirect_call(self, graphs, seen=None):
        results = []
        for graph in graphs:
            results.append(self.analyze_direct_call(graph, seen))
        return self.join_results(results)

    def analyze_oosend(self, TYPE, name, seen=None):
        graphs = TYPE._lookup_graphs(name)
        return self.analyze_indirect_call(graphs, seen)

    def analyze_all(self, graphs=None):
        if graphs is None:
            graphs = self.translator.graphs
        for graph in graphs:
            for block, op in graph.iterblockops():
                self.analyze(op)


class DependencyTracker(object):
    """This tracks the analysis of cyclic call graphs."""

    # The point is that one analyzer works fine if the question we ask
    # it is about a single graph, but in the case of recursion, it will
    # fail if we ask it about multiple graphs.  The purpose of this
    # class is to fix the cache in GraphAnalyzer._analyzed_calls after
    # each round, whenever a new set of graphs have been added to it.
    # It works by assuming that we can simply use 'join_two_results'
    # in order to do so.

    def __init__(self, analyzer):
        self.analyzer = analyzer
        # mapping {graph: result} (shared with GraphAnalyzer._analyzed_calls)
        self.graph_results = analyzer._analyzed_calls
        # mapping {graph: set_of_graphs_that_depend_on_it}
        self.backward_dependencies = {}
        # the current stack of graphs being analyzed
        self.current_stack = []
        # the set of graphs at which recursion occurs
        self.recursion_points = set()

    def enter(self, graph):
        if self.current_stack:
            caller_graph = self.current_stack[-1]
            # record a dependency between the old graph and the new one,
            # i.e. going backward: FROM the new graph...
            deps = self.backward_dependencies.setdefault(graph, set())
            deps.add(caller_graph)                  # ... TO the caller one.
        #
        if graph not in self.graph_results:
            self.current_stack.append(graph)
            self.graph_results[graph] = Ellipsis
            return True
        else:
            self.recursion_points.add(graph)
            return False

    def leave_with(self, result):
        graph = self.current_stack.pop()
        assert self.graph_results[graph] is Ellipsis
        self.graph_results[graph] = result
        #
        if not self.current_stack:
            self._propagate_backward_recursion()

    def get_cached_result(self, graph):
        result = self.graph_results[graph]
        if result is Ellipsis:
            return self.analyzer.bottom_result()
        return result

    def _propagate_backward_recursion(self):
        # called at the end of the analysis.  We need to back-propagate
        # the results to all graphs, starting from the graphs in
        # 'recursion_points', if any.
        recpts = self.recursion_points
        bwdeps = self.backward_dependencies
        grpres = self.graph_results
        join_two_res = self.analyzer.join_two_results
        while recpts:
            callee_graph = recpts.pop()
            result = grpres[callee_graph]
            for caller_graph in bwdeps.get(callee_graph, ()):
                oldvalue1 = grpres[caller_graph]
                result1 = join_two_res(result, oldvalue1)
                if result1 != oldvalue1:
                    grpres[caller_graph] = result1
                    recpts.add(caller_graph)


class BoolGraphAnalyzer(GraphAnalyzer):
    """generic way to analyze graphs: recursively follow it until the first
    operation is found on which self.analyze_simple_operation returns True"""

    @staticmethod
    def join_two_results(result1, result2):
        return result1 or result2

    @staticmethod
    def is_top_result(result):
        return result

    @staticmethod
    def bottom_result():
        return False

    @staticmethod
    def top_result():
        return True

