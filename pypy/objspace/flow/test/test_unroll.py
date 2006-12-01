import operator
from pypy.objspace.flow.test.test_objspace import Base
from pypy.rlib.unroll import unrolling_zero, unrolling_iterable

class TestUnroll(Base):

    def test_unrolling_int(self):
        l = range(10)
        def f(tot):
            i = unrolling_zero
            while i < len(l):
                tot += l[i]
                i = i + 1
            return tot*2
        assert f(0) == sum(l)*2

        graph = self.codetest(f)
        ops = self.all_operations(graph)
        assert ops == {'inplace_add': 10, 'mul': 1}

    def test_unroller(self):
        l = unrolling_iterable(range(10))
        def f(tot):
            for v in l:
                tot += v
            return tot*3
        assert f(0) == sum(l)*3

        graph = self.codetest(f)
        ops = self.all_operations(graph)
        assert ops == {'inplace_add': 10, 'mul': 1}

    def test_unroll_setattrs(self):
        values_names = unrolling_iterable(enumerate(['a', 'b', 'c']))
        def f(x):
            for v, name in values_names:
                setattr(x, name, v)

        graph = self.codetest(f)
        ops = self.all_operations(graph)
        assert ops == {'setattr': 3}

    def test_unroll_ifs(self):
        operations = unrolling_iterable([operator.lt,
                                         operator.le,
                                         operator.eq,
                                         operator.ne,
                                         operator.gt,
                                         operator.ge])
        def accept(n):
            "stub"
        def f(x, y):
            for op in operations:
                if accept(op):
                    op(x, y)

        graph = self.codetest(f)
        ops = self.all_operations(graph)
        assert ops == {'simple_call': 6,
                       'is_true': 6,
                       'lt': 1,
                       'le': 1,
                       'eq': 1,
                       'ne': 1,
                       'gt': 1,
                       'ge': 1}
