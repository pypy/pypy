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

    def test_nested_scope_locals(self):
        def f():
            x = 3
            def g():
                i = x
                return locals()
            return g()
        d = f()
        self.assertEquals(d, {'i':3})

    def test_deeply_nested_scope_locals(self):
        def f():
            x = 3
            def g():
                def h():
                    i = x
                    return locals()
                return locals(), h()
            return g()
        outer_locals, inner_locals = f()
        self.assertEquals(inner_locals, {'i':3})
        self.assertEquals(len(outer_locals), 1, "len!=1 for %r" % outer_locals)

if __name__ == '__main__':
    test.main()
