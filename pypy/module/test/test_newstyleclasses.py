import autopath

from pypy.tool import testit

class TestBuiltinApp(testit.AppTestCase):
    def setUp(self):
        self.space = testit.objspace()

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
            def _del(self): raise KeyError
            name = property(_get, _set, _del)
        a1 = a()
        self.assertEquals(a1.name, 42)
        self.assertRaises(AttributeError, setattr, a1, 'name', 42)
        self.assertRaises(KeyError, delattr, a1, 'name')

    def test_super(self):
        class A(object):
            def f(self):
                return 'A'
        class B(A):
            def f(self):
                return 'B' + super(B,self).f()
        class C(A):
            def f(self):
                return 'C' + super(C,self).f()
        class D(B, C):
            def f(self):
                return 'D' + super(D,self).f()
        d = D()
        self.assertEquals(d.f(), "DBCA")
        self.assertEquals(D.__mro__, (D, B, C, A, object))

    def test_super_metaclass(self):
        class xtype(type):
            def __init__(self, name, bases, dict):
                super(xtype, self).__init__(name, bases, dict)
        A = xtype('A', (), {})
        self.assert_(isinstance(A, xtype))
        a = A()
        self.assert_(isinstance(a, A))

if __name__ == '__main__':
    testit.main()
