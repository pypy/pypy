from pypy.translator.backendopt import graphanalyze
reload(graphanalyze)

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

    def analyze_simple_operation(self, op):
        if op.opname == "setfield":
            return frozenset([
                ("struct", op.args[0].concretetype, op.args[1].value)])
        elif op.opname == "setarrayitem":
            return frozenset([("array", op.args[0].concretetype)])
        return empty_set

    def analyze_external_call(self, op):
        return self.bottom_result() # an external call cannot change anything

