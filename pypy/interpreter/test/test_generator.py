from __future__ import generators
import autopath

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
