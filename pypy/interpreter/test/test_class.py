import autopath
from pypy.tool import testit


class TestClassApp(testit.AppTestCase):
    
    def test_class(self):
        class C:
            pass
        self.assertEquals(C.__class__, type)
        c = C()
        self.assertEquals(c.__class__, C)

    def test_metaclass_explicit(self):
        class M(type):
            pass
        class C:
            __metaclass__ = M
        self.assertEquals(C.__class__, M)
        c = C()
        self.assertEquals(c.__class__, C)

    def test_metaclass_inherited(self):
        class M(type):
            pass
        class B:
            __metaclass__ = M
        class C(B):
            pass
        self.assertEquals(C.__class__, M)
        c = C()
        self.assertEquals(c.__class__, C)

    def test_metaclass_global(self):
        d = {}
        metatest_text = """
class M(type):
    pass

__metaclass__ = M

class C:
    pass
"""
        exec metatest_text in d
        C = d['C']
        M = d['M']
        self.assertEquals(C.__class__, M)
        c = C()
        self.assertEquals(c.__class__, C)

    def test_method(self):
        class C:
            def meth(self):
                return 1
        c = C()
        self.assertEqual(c.meth(), 1)

    def test_method_exc(self):
        class C:
            def meth(self):
                raise RuntimeError
        c = C()
        self.assertRaises(RuntimeError, c.meth)

    def test_class_attr(self):
        class C:
            a = 42
        c = C()
        self.assertEquals(c.a, 42)
        self.assertEquals(C.a, 42)

    def test_class_attr_inherited(self):
        class C:
            a = 42
        class D(C):
            pass
        d = D()
        self.assertEquals(d.a, 42)
        self.assertEquals(D.a, 42)

    def test___new__(self):
        class A(object):
            pass
        self.assert_(isinstance(A(), A))
        self.assert_(isinstance(object.__new__(A), A))
        self.assert_(isinstance(A.__new__(A), A))

    def test_int_subclass(self):
        class R(int):
            pass
        x = R(5)
        self.assertEquals(type(x), R)
        self.assertEquals(x, 5)
        self.assertEquals(type(int(x)), int)
        self.assertEquals(int(x), 5)

    def test_long_subclass(self):
        class R(long):
            pass
        x = R(5L)
        self.assertEquals(type(x), R)
        self.assertEquals(x, 5L)
        self.assertEquals(type(long(x)), long)
        self.assertEquals(long(x), 5L)

    def test_float_subclass(self):
        class R(float):
            pass
        x = R(5.5)
        self.assertEquals(type(x), R)
        self.assertEquals(x, 5.5)
        self.assertEquals(type(float(x)), float)
        self.assertEquals(float(x), 5.5)

    def test_meth_doc(self):
        class C:
            def meth_no_doc(self):
                pass
            def meth_doc(self):
                """this is a docstring"""
                pass
        c = C()
        self.assertEquals(C.meth_no_doc.__doc__, None)
        self.assertEquals(c.meth_no_doc.__doc__, None)
        self.assertEquals(C.meth_doc.__doc__, """this is a docstring""")
        self.assertEquals(c.meth_doc.__doc__, """this is a docstring""")

    def test_getattribute(self):
        class C:
            def __getattribute__(self, attr):
                if attr == 'one':
                    return 'two'
                return super(C, self).__getattribute__(attr)
        c = C()
        self.assertEquals(c.one, "two")
        self.assertRaises(AttributeError, getattr, c, "two")

if __name__ == '__main__':
    testit.main()
