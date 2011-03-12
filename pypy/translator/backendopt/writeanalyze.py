from pypy.objspace.flow.model import Variable
from pypy.translator.backendopt import graphanalyze
from pypy.rpython.ootypesystem import ootype

top_set = object()
empty_set = frozenset()

class WriteAnalyzer(graphanalyze.GraphAnalyzer):

    @staticmethod
    def join_two_results(result1, result2):
        if result1 is top_set:
            return top_set
        if result2 is top_set:
            return top_set
        return result1.union(result2)

    @staticmethod
    def bottom_result():
        return empty_set

    @staticmethod
    def top_result():
        return top_set

    @staticmethod
    def is_top_result(result):
        return result is top_set

    def analyze_simple_operation(self, op, graphinfo):
        if op.opname in ("setfield", "oosetfield"):
            if graphinfo is None or not graphinfo.is_fresh_malloc(op.args[0]):
                return frozenset([
                    ("struct", op.args[0].concretetype, op.args[1].value)])
        elif op.opname == "setarrayitem":
            if graphinfo is None or not graphinfo.is_fresh_malloc(op.args[0]):
                return self._array_result(op.args[0].concretetype)
        return empty_set

    def _array_result(self, TYPE):
        return frozenset([("array", TYPE)])

    def analyze_external_method(self, op, TYPE, meth):
        if isinstance(TYPE, ootype.Array):
            methname = op.args[0].value
            if methname == 'll_setitem_fast':
                return self._array_result(op.args[1].concretetype)
            elif methname in ('ll_getitem_fast', 'll_length'):
                return self.bottom_result()
        return graphanalyze.GraphAnalyzer.analyze_external_method(self, op, TYPE, meth)

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
