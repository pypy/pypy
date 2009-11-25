from pypy.conftest import option

class AppTestObject:

    def setup_class(cls):
        import sys
        cpython_behavior = (not option.runappdirect
                            or not hasattr(sys, 'pypy_translation_info'))
                
        cls.w_cpython_behavior = cls.space.wrap(cpython_behavior)        
    
    def test_hash_builtin(self):
        if not self.cpython_behavior:
            skip("on pypy-c id == hash is not guaranteed")
        import sys
        o = object()
        assert (hash(o) & sys.maxint) == (id(o) & sys.maxint)

    def test_hash_method(self):
        o = object()
        assert hash(o) == o.__hash__() 

    def test_hash_list(self):
        l = range(5)
        raises(TypeError, hash, l)

    def test_no_getnewargs(self):
        o = object()
        assert not hasattr(o, '__getnewargs__')

    def test_hash_subclass(self):
        import sys
        class X(object):
            pass
        x = X()
        if self.cpython_behavior:
            assert (hash(x) & sys.maxint) == (id(x) & sys.maxint)
        assert hash(x) == object.__hash__(x)

    def test_reduce_recursion_bug(self):
        class X(object):
            def __reduce__(self):
                return object.__reduce__(self) + (':-)',)
        s = X().__reduce__()
        assert s[-1] == ':-)'
