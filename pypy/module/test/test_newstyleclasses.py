import autopath

from pypy.tool import test

class TestBuiltinApp(test.AppTestCase):
    def setUp(self):
        self.space = test.objspace()

    def test_staticmethod(self):
        class C:
            def f(a, b):
                return a+b
            f = staticmethod(f)
        class D(C):
            pass

        c = C()
        d = D()
        self.assertEquals(c.f("abc", "def"), "abcdef")
        self.assertEquals(C.f("abc", "def"), "abcdef")
        self.assertEquals(d.f("abc", "def"), "abcdef")
        self.assertEquals(D.f("abc", "def"), "abcdef")

    def test_classmethod(self):
        class C:
            def f(cls, stuff):
                return cls, stuff
            f = classmethod(f)
        class D(C):
            pass

        c = C()
        d = D()
        self.assertEquals(c.f("abc"), (C, "abc"))
        self.assertEquals(C.f("abc"), (C, "abc"))
        self.assertEquals(d.f("abc"), (D, "abc"))
        self.assertEquals(D.f("abc"), (D, "abc"))

    def test_property_simple(self):
        
        class a(object):
            def _get(self): return 42
            def _set(self, value): raise AttributeError
            def _del(self, value): raise KeyError
            name = property(_get, _set, _del)
        a1 = a()
        self.assertEquals(a1.name, 42)
        self.assertRaises(AttributeError, setattr, a1, 'name')
        self.assertRaises(KeyError, delattr, a1, 'name')

if __name__ == '__main__':
    test.main()
