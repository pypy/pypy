from __future__ import generators
import autopath
from pypy.tool import test

class AppTestGenerator(test.AppTestCase):

    def test_generator(self):
        def f():
            yield 1
        self.assertEquals(f().next(), 1)

    def test_generator2(self):
        def f():
            yield 1
        g = f()
        self.assertEquals(g.next(), 1)
        self.assertRaises(StopIteration, g.next)

    def test_generator3(self):
        def f():
            yield 1
        g = f()
        self.assertEquals(list(g), [1])

    def test_generator4(self):
        def f():
            yield 1
        g = f()
        self.assertEquals([x for x in g], [1])

    def test_generator_explicit_stopiteration(self):
        def f():
            yield 1
            raise StopIteration
        g = f()
        self.assertEquals([x for x in g], [1])

    def test_generator_propagate_stopiteration(self):
        def f():
            it = iter([1])
            while 1: yield it.next()
        g = f()
        self.assertEquals([x for x in g], [1])

    def test_generator_restart(self):
        def g():
            i = me.next()
            yield i
        me = g()
        self.assertRaises(ValueError, me.next)


if __name__ == '__main__':
    test.main()
