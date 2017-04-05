
class AppTestClass: 

    def test_class(self):
        class C(object):
            pass
        assert C.__class__ == type
        c = C()
        assert c.__class__ == C

    def test_metaclass_explicit(self):
        class M(type):
            pass
        class C:
            __metaclass__ = M
        assert C.__class__ == M
        c = C()
        assert c.__class__ == C

    def test_metaclass_inherited(self):
        class M(type):
            pass
        class B:
            __metaclass__ = M
        class C(B):
            pass
        assert C.__class__ == M
        c = C()
        assert c.__class__ == C

    def test_metaclass_global(self):
        d = {}
        metatest_text = """if 1: 
            class M(type):
                pass

            __metaclass__ = M

            class C:
                pass\n"""
        exec metatest_text in d
        C = d['C']
        M = d['M']
        assert C.__class__ == M
        c = C()
        assert c.__class__ == C

    def test_method(self):
        class C(object):
            def meth(self):
                return 1
        c = C()
        assert c.meth() == 1

    def test_method_exc(self):
        class C(object):
            def meth(self):
                raise RuntimeError
        c = C()
        raises(RuntimeError, c.meth)

    def test_class_attr(self):
        class C(object):
            a = 42
        c = C()
        assert c.a == 42
        assert C.a == 42

    def test_class_attr_inherited(self):
        class C(object):
            a = 42
        class D(C):
            pass
        d = D()
        assert d.a == 42
        assert D.a == 42

    def test___new__(self):
        class A(object):
            pass
        assert isinstance(A(), A)
        assert isinstance(object.__new__(A), A)
        assert isinstance(A.__new__(A), A)

    def test_int_subclass(self):
        class R(int):
            pass
        x = R(5)
        assert type(x) == R
        assert x == 5
        assert type(int(x)) == int
        assert int(x) == 5

    def test_long_subclass(self):
        class R(long):
            pass
        x = R(5L)
        assert type(x) == R
        assert x == 5L
        assert type(long(x)) == long
        assert long(x) == 5L

    def test_float_subclass(self):
        class R(float):
            pass
        x = R(5.5)
        assert type(x) == R
        assert x == 5.5
        assert type(float(x)) == float
        assert float(x) == 5.5

    def test_meth_doc(self):
        class C(object):
            def meth_no_doc(self):
                pass
            def meth_doc(self):
                """this is a docstring"""
                pass
        c = C()
        assert C.meth_no_doc.__doc__ == None
        assert c.meth_no_doc.__doc__ == None
        assert C.meth_doc.__doc__ == """this is a docstring"""
        assert c.meth_doc.__doc__ == """this is a docstring"""

    def test_getattribute(self):
        class C(object):
            def __getattribute__(self, attr):
                if attr == 'one':
                    return 'two'
                return super(C, self).__getattribute__(attr)
        c = C()
        assert c.one == "two"
        raises(AttributeError, getattr, c, "two")
