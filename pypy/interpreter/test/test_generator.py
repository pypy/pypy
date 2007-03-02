from __future__ import generators

class AppTestGenerator:

    def test_generator(self):
        def f():
            yield 1
        assert f().next() == 1

    def test_generator2(self):
        def f():
            yield 1
        g = f()
        assert g.next() == 1
        raises(StopIteration, g.next)

    def test_generator3(self):
        def f():
            yield 1
        g = f()
        assert list(g) == [1]

    def test_generator4(self):
        def f():
            yield 1
        g = f()
        assert [x for x in g] == [1]

    def test_generator_explicit_stopiteration(self):
        def f():
            yield 1
            raise StopIteration
        g = f()
        assert [x for x in g] == [1]

    def test_generator_propagate_stopiteration(self):
        def f():
            it = iter([1])
            while 1: yield it.next()
        g = f()
        assert [x for x in g] == [1]

    def test_generator_restart(self):
        def g():
            i = me.next()
            yield i
        me = g()
        raises(ValueError, me.next)

    def test_generator_expression(self):
        import sys
        if sys.version_info < (2, 4):
            skip("generator expressions only work on Python >= 2.4")
        exec "res = sum(i*i for i in range(5))"
        assert res == 30

    def test_generator_expression_2(self):
        import sys
        if sys.version_info < (2, 4):
            skip("generator expressions only work on Python >= 2.4")
        d = {}
        exec """
def f():
    total = sum(i for i in [x for x in z])
    return total, x
z = [1, 2, 7]
res = f()
""" in d
        assert d['res'] == (10, 7)
