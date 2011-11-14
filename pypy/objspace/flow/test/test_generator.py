from pypy.objspace.flow.test.test_objspace import Base


class TestGenerator(Base):

    def test_simple_generator(self):
        def f(n):
            i = 0
            while i < n:
                yield i
                yield i
                i += 1
        graph = self.codetest(f)
        ops = self.all_operations(graph)
        assert ops == {'generator_entry': 1,
                       'lt': 1, 'is_true': 1,
                       'yield': 2,
                       'inplace_add': 1}
