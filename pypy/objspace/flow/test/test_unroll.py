from pypy.objspace.flow.test.test_objspace import Base
from pypy.rpython.unroll import unrolling_zero, unrolling_iterable

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
