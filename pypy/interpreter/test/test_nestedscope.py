import autopath
from pypy.tool import test


class AppTestNestedScope(test.AppTestCase):

    def test_nested_scope(self):
        x = 42
        def f(): return x
        self.assertEquals(f(), 42)

    def test_nested_scope2(self):
        x = 42
        y = 3
        def f(): return x
        self.assertEquals(f(), 42)

    def test_nested_scope3(self):
        x = 42
        def f():
            def g():
                return x
            return g
        self.assertEquals(f()(), 42)

    def test_nested_scope4(self):
        def f():
            x = 3
            def g():
                return x
            a = g()
            x = 4
            b = g()
            return (a, b)
        self.assertEquals(f(), (3, 4))


if __name__ == '__main__':
    test.main()
