from rpython.translator.simplify import get_graph, get_funcobj
from pypy.tool.algo.unionfind import UnionFind


class GraphAnalyzer(object):
    verbose = False

    def __init__(self, translator):
        self.translator = translator
        self._analyzed_calls = UnionFind(lambda graph: Dependency(self))

    # method overridden by subclasses

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

    @staticmethod
    def result_builder():
        raise NotImplementedError("abstract base class")

    @staticmethod
    def add_to_result(result, other):
        raise NotImplementedError("abstract base class")

    @staticmethod
    def finalize_builder(result):
        raise NotImplementedError("abstract base class")

    @staticmethod
    def join_two_results(result1, result2):
        raise NotImplementedError("abstract base class")

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
        result = self.result_builder()
        graphinfo = self.compute_graph_info(graph)
        for block in graph.iterblocks():
            if block is graph.startblock:
                result = self.add_to_result(
                    result,
                    self.analyze_startblock(block, seen)
                )
            elif block is graph.exceptblock:
                result = self.add_to_result(
                    result,
                    self.analyze_exceptblock(block, seen)
                )
            if not self.is_top_result(result):
                for op in block.operations:
                    result = self.add_to_result(
                        result,
                        self.analyze(op, seen, graphinfo)
                    )
                    if self.is_top_result(result):
                        break
            if not self.is_top_result(result):
                for exit in block.exits:
                    result = self.add_to_result(
                        result,
                        self.analyze_link(exit, seen)
                    )
                    if self.is_top_result(result):
                        break
            if self.is_top_result(result):
                break
        result = self.finalize_builder(result)
        seen.leave_with(result)
        return result

    def analyze_indirect_call(self, graphs, seen=None):
        result = self.result_builder()
        for graph in graphs:
            result = self.add_to_result(
                result,
                self.analyze_direct_call(graph, seen)
            )
            if self.is_top_result(result):
                break
        return self.finalize_builder(result)

    def analyze_oosend(self, TYPE, name, seen=None):
        graphs = TYPE._lookup_graphs(name)
        return self.analyze_indirect_call(graphs, seen)

    def analyze_all(self, graphs=None):
        if graphs is None:
            graphs = self.translator.graphs
        for graph in graphs:
            for block, op in graph.iterblockops():
                self.analyze(op)


class Dependency(object):
    def __init__(self, analyzer):
        self._analyzer = analyzer
        self._result = analyzer.bottom_result()

    def merge_with_result(self, result):
        self._result = self._analyzer.join_two_results(self._result, result)

    def absorb(self, other):
        self.merge_with_result(other._result)


class DependencyTracker(object):
    """This tracks the analysis of cyclic call graphs."""

    # The point is that GraphAnalyzer works fine if the question we ask
    # is about a single graph; but in the case of recursion, it will
    # fail if we ask about multiple graphs.  The purpose of this
    # class is to fix the cache in GraphAnalyzer._analyzed_calls after
    # each round, whenever a new set of graphs have been added to it.
    # It works by assuming that the following is correct: for any set of
    # graphs that can all (indirectly) call each other, all these graphs
    # will get the same answer that is the 'join_two_results' of all of
    # them.

    def __init__(self, analyzer):
        self.analyzer = analyzer
        # the UnionFind object, which works like a mapping {graph: Dependency}
        # (shared with GraphAnalyzer._analyzed_calls)
        self.graph_results = analyzer._analyzed_calls
        # the current stack of graphs being analyzed
        self.current_stack = []
        self.current_stack_set = set()

    def enter(self, graph):
        if graph not in self.graph_results:
            self.current_stack.append(graph)
            self.current_stack_set.add(graph)
            self.graph_results.find(graph)
            return True
        else:
            if graph in self.current_stack_set:
                # found a cycle; merge all graphs in that cycle
                i = len(self.current_stack) - 1
                while self.current_stack[i] is not graph:
                    self.graph_results.union(self.current_stack[i], graph)
                    i -= 1
            return False

    def leave_with(self, result):
        graph = self.current_stack.pop()
        self.current_stack_set.remove(graph)
        dep = self.graph_results[graph]
        dep.merge_with_result(result)

    def get_cached_result(self, graph):
        dep = self.graph_results[graph]
        return dep._result


class BoolGraphAnalyzer(GraphAnalyzer):
    """generic way to analyze graphs: recursively follow it until the first
    operation is found on which self.analyze_simple_operation returns True"""

    def bottom_result(self):
        return False

    def top_result(self):
        return True

    def is_top_result(self, result):
        return result

    def result_builder(self):
        return False

    def add_to_result(self, result, other):
        return self.join_two_results(result, other)

    def finalize_builder(self, result):
        return result

    def join_two_results(self, result1, result2):
        return result1 or result2
