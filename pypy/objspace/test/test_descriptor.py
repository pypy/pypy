import autopath

class AppTest_Descriptor:

    def test_non_data_descr(self):
        class X(object):
            def f(self):
                return 42
        x = X()
        assert x.f() == 42
        x.f = 43
        assert x.f == 43
        del x.f
        assert x.f() == 42

    def test_member(self):
        class X(object):
            def __init__(self):
                self._v = 0
            def get_v(self):
                return self._v
            def set_v(self, v):
                self._v = v
            v = property(get_v, set_v)
        x = X()
        assert x.v  == 0
        assert X.v.__get__(x) == 0
        x.v = 1
        assert x.v == 1
        X.v.__set__(x, 0)
        assert x.v == 0
        raises(AttributeError, delattr, x, 'v')
        raises(AttributeError, X.v.__delete__, x)

    def test_special_methods_returning_strings(self): 
        class A: 
            seen = []
            def __str__(self): 
                self.seen.append(1) 
            def __repr__(self): 
                self.seen.append(2) 
            def __oct__(self): 
                self.seen.append(3) 
            def __hex__(self): 
                self.seen.append(4) 

        inst = A()
        raises(TypeError, str, inst) 
        raises(TypeError, repr, inst) 
        raises(TypeError, oct, inst) 
        raises(TypeError, hex, inst) 
        assert A.seen == [1,2,3,4]

class TestDesciprtorOnStd: 
    objspacename = 'std' 
    def test_hash(self): 
        class A:
            pass 
        hash(A()) 
        class B: 
            def __eq__(self, other): pass 
        raises(TypeError, hash, B()) 
        class C: 
            def __cmp__(self, other): pass 
        raises(TypeError, "hash(C())")

        class D: 
            def __hash__(self): 
                return 23L
        raises(TypeError, hash, D())

        class E: 
            def __hash__(self): 
                return "something"
        raises(TypeError, hash, E())
