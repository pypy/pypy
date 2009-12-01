from pypy.translator.simplify import get_graph, get_funcobj
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
from pypy.rpython.lltypesystem import lltype

class GraphAnalyzer(object):
    def __init__(self, translator):
        self.translator = translator
        self.analyzed_calls = {}
        self.recursion_hit = False

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

    def analyze_simple_operation(self, op):
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

    def analyze(self, op, seen=None):
        if op.opname == "direct_call":
            graph = get_graph(op.args[0], self.translator)
            if graph is None:
                return self.analyze_external_call(op, seen)
            return self.analyze_direct_call(graph, seen)
        elif op.opname == "indirect_call":
            if op.args[-1].value is None:
                return self.top_result()
            return self.analyze_indirect_call(op.args[-1].value, seen)
        elif op.opname == "oosend":
            name = op.args[0].value
            TYPE = op.args[1].concretetype
            _, meth = TYPE._lookup(name)
            graph = getattr(meth, 'graph', None)
            if graph is None:
                return self.analyze_external_method(op, TYPE, meth)
            return self.analyze_oosend(TYPE, name, seen)
        return self.analyze_simple_operation(op)

    def analyze_direct_call(self, graph, seen=None):
        if graph in self.analyzed_calls:
            return self.analyzed_calls[graph]
        if seen is None:
            seen = set([graph])
            self.recursion_hit = False
            started_here = True
        elif graph in seen:
            self.recursion_hit = True
            return self.bottom_result()
        else:
            started_here = False
            seen.add(graph)
        result = self.bottom_result()
        for block in graph.iterblocks():
            if block is graph.startblock:
                result = self.join_two_results(
                        result, self.analyze_startblock(block, seen))
            elif block is graph.exceptblock:
                result = self.join_two_results(
                        result, self.analyze_exceptblock(block, seen))
            for op in block.operations:
                result = self.join_two_results(
                        result, self.analyze(op, seen))
            for exit in block.exits:
                result = self.join_two_results(
                        result, self.analyze_link(exit, seen))
            if self.is_top_result(result):
                self.analyzed_calls[graph] = result
                return result
        if not self.recursion_hit or started_here:
            self.analyzed_calls[graph] = result
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

