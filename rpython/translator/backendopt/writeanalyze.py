from rpython.flowspace.model import Variable
from rpython.translator.backendopt import graphanalyze

top_set = object()
empty_set = frozenset()

CUTOFF = 1000

class WriteAnalyzer(graphanalyze.GraphAnalyzer):
    def bottom_result(self):
        return empty_set

    def top_result(self):
        return top_set

    def is_top_result(self, result):
        return result is top_set

    def result_builder(self):
        return set()

    def add_to_result(self, result, other):
        if other is top_set:
            return top_set
        if len(other) + len(result) > CUTOFF:
            return top_set
        result.update(other)
        return result

    def finalize_builder(self, result):
        if result is top_set:
            return result
        return frozenset(result)

    def join_two_results(self, result1, result2):
        if result1 is top_set or result2 is top_set:
            return top_set
        return result1.union(result2)

    def analyze_simple_operation(self, op, graphinfo):
        if op.opname == "setfield":
            if graphinfo is None or not graphinfo.is_fresh_malloc(op.args[0]):
                return frozenset([
                    ("struct", op.args[0].concretetype, op.args[1].value)])
        elif op.opname == "setarrayitem":
            if graphinfo is None or not graphinfo.is_fresh_malloc(op.args[0]):
                return self._array_result(op.args[0].concretetype)
        return empty_set

    def _array_result(self, TYPE):
        return frozenset([("array", TYPE)])

    def compute_graph_info(self, graph):
        return FreshMallocs(graph)


class FreshMallocs(object):
    def __init__(self, graph):
        self.nonfresh = set(graph.getargs())
        pendingblocks = list(graph.iterblocks())
        self.allvariables = set()
        for block in pendingblocks:
            self.allvariables.update(block.inputargs)
        pendingblocks.reverse()
        while pendingblocks:
            block = pendingblocks.pop()
            for op in block.operations:
                self.allvariables.add(op.result)
                if (op.opname == 'malloc' or op.opname == 'malloc_varsize'
                    or op.opname == 'new'):
                    continue
                elif op.opname in ('cast_pointer', 'same_as'):
                    if self.is_fresh_malloc(op.args[0]):
                        continue
                self.nonfresh.add(op.result)
            for link in block.exits:
                self.nonfresh.update(link.getextravars())
                self.allvariables.update(link.getextravars())
                prevlen = len(self.nonfresh)
                for v1, v2 in zip(link.args, link.target.inputargs):
                    if not self.is_fresh_malloc(v1):
                        self.nonfresh.add(v2)
                if len(self.nonfresh) > prevlen:
                    pendingblocks.append(link.target)

    def is_fresh_malloc(self, v):
        if not isinstance(v, Variable):
            return False
        assert v in self.allvariables
        return v not in self.nonfresh


class ReadWriteAnalyzer(WriteAnalyzer):

    def analyze_simple_operation(self, op, graphinfo):
        if op.opname == "getfield":
            return frozenset([
                ("readstruct", op.args[0].concretetype, op.args[1].value)])
        elif op.opname == "getarrayitem":
            return frozenset([
                ("readarray", op.args[0].concretetype)])
        return WriteAnalyzer.analyze_simple_operation(self, op, graphinfo)
