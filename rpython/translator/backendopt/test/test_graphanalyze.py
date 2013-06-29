import random
from rpython.tool.algo.unionfind import UnionFind
from rpython.translator.backendopt.graphanalyze import Dependency
from rpython.translator.backendopt.graphanalyze import DependencyTracker


class FakeGraphAnalyzer:
    def __init__(self):
        self._analyzed_calls = UnionFind(lambda graph: Dependency(self))

    @staticmethod
    def bottom_result():
        return 0

    @staticmethod
    def join_two_results(result1, result2):
        return result1 | result2


def test_random_graphs():
    for _ in range(100):
        N = 10
        edges = [(random.randrange(N), random.randrange(N))
                     for i in range(N*N//3)]

        def expected(node1):
            prev = set()
            seen = set([node1])
            while len(seen) > len(prev):
                prev = set(seen)
                for a, b in edges:
                    if a in seen:
                        seen.add(b)
            return sum([1 << n for n in seen])

        def rectrack(n, tracker):
            if not tracker.enter(n):
                return tracker.get_cached_result(n)
            result = 1 << n
            for a, b in edges:
                if a == n:
                    result |= rectrack(b, tracker)
            tracker.leave_with(result)
            return result

        analyzer = FakeGraphAnalyzer()
        for n in range(N):
            tracker = DependencyTracker(analyzer)
            method1 = rectrack(n, tracker)
            method2 = expected(n)
            assert method1 == method2
