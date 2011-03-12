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
        if graphinfo and op.args[0] in graphinfo:
            return empty_set
        if op.opname in ("setfield", "oosetfield"):
            return frozenset([
                ("struct", op.args[0].concretetype, op.args[1].value)])
        elif op.opname == "setarrayitem":
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
        newstructs = set()
        for block in graph.iterblocks():
            for op in block.operations:
                if (op.opname == 'malloc' or op.opname == 'malloc_varsize'
                    or op.opname == 'new'):
                    newstructs.add(op.result)
                elif op.opname in ('cast_pointer', 'same_as'):
                    if op.args[0] in newstructs:
                        newstructs.add(op.result)
        return newstructs


class ReadWriteAnalyzer(WriteAnalyzer):

    def analyze_simple_operation(self, op, graphinfo):
        if op.opname == "getfield":
            return frozenset([
                ("readstruct", op.args[0].concretetype, op.args[1].value)])
        elif op.opname == "getarrayitem":
            return frozenset([
                ("readarray", op.args[0].concretetype)])
        return WriteAnalyzer.analyze_simple_operation(self, op, graphinfo)
