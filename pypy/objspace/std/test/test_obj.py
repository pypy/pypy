from __future__ import with_statement
from pypy.conftest import option

class AppTestObject:

    def setup_class(cls):
        from pypy.interpreter import gateway
        import sys
        cpython_behavior = (not option.runappdirect
                            or not hasattr(sys, 'pypy_translation_info'))

        cls.w_cpython_behavior = cls.space.wrap(cpython_behavior)
        cls.w_cpython_version = cls.space.wrap(tuple(sys.version_info))
        space = cls.space

        def w_unwrap_wrap_unicode(space, w_obj):
            return space.wrap(space.unicode_w(w_obj))
        cls.w_unwrap_wrap_unicode = space.wrap(gateway.interp2app(w_unwrap_wrap_unicode))
        def w_unwrap_wrap_str(space, w_obj):
            return space.wrap(space.str_w(w_obj))
        cls.w_unwrap_wrap_str = space.wrap(gateway.interp2app(w_unwrap_wrap_str))

    def test_hash_builtin(self):
        if not self.cpython_behavior:
            skip("on pypy-c id == hash is not guaranteed")
        if self.cpython_version >= (2, 7):
            skip("on CPython >= 2.7, id != hash")
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
        if self.cpython_behavior and self.cpython_version < (2, 7):
            assert (hash(x) & sys.maxint) == (id(x) & sys.maxint)
        assert hash(x) == object.__hash__(x)

    def test_reduce_recursion_bug(self):
        class X(object):
            def __reduce__(self):
                return object.__reduce__(self) + (':-)',)
        s = X().__reduce__()
        assert s[-1] == ':-)'

    def test_default_format(self):
        class x(object):
            def __str__(self):
                return "Pickle"
            def __unicode__(self):
                return u"Cheese"
        res = format(x())
        assert res == "Pickle"
        assert isinstance(res, str)
        res = format(x(), u"")
        assert res == u"Cheese"
        assert isinstance(res, unicode)
        del x.__unicode__
        res = format(x(), u"")
        assert res == u"Pickle"
        assert isinstance(res, unicode)

    def test_subclasshook(self):
        class x(object):
            pass
        assert x().__subclasshook__(object()) is NotImplemented
        assert x.__subclasshook__(object()) is NotImplemented

    def test_object_init(self):
        import warnings

        class A(object):
            pass

        raises(TypeError, A().__init__, 3)
        raises(TypeError, A().__init__, a=3)

        class B(object):
            def __new__(cls):
                return super(B, cls).__new__(cls)

            def __init__(self):
                super(B, self).__init__(a=3)

        #-- pypy doesn't raise the DeprecationWarning
        #with warnings.catch_warnings(record=True) as log:
        #    warnings.simplefilter("always", DeprecationWarning)
        #    B()
        #assert len(log) == 1
        #assert log[0].message.args == ("object.__init__() takes no parameters",)
        #assert type(log[0].message) is DeprecationWarning

    def test_object_str(self):
        # obscure case: __str__() must delegate to __repr__() without adding
        # type checking on its own
        class A(object):
            def __repr__(self):
                return 123456
        assert A().__str__() == 123456

    def test_object_identity(self):
        assert 1 is 1
        x = 1000000
        assert x + 1 is int(str(x + 1))
        assert 1 is not 1.0
        assert 1 is not 1l
        assert 1l is not 1.0
        assert 1.1 is 1.1
        for x in range(10):
            assert x + 0.1 is x + 0.1
        for x in range(10):
            assert x + 1L is x + 1L
        #for x in range(10):
        #    assert x+1j is x+1j
        l = [1]
        assert l[0] is l[0]
        l = ["a"]
        assert l[0] is l[0]
        u = u"a"
        assert self.unwrap_wrap_unicode(u) is u

    def test_id(self):
        assert id(1) == (1 << 3) + 1
        assert id(1l) == (1 << 3) + 3
        class myint(int):
            pass
        assert id(myint(1)) != id(1)

        assert id(1.0) & 7 == 5
        assert id(-0.0) != id(0.0)
        assert hex(id(2.0)) == '0x20000000000000005L'
        assert id(0.0) == 5

        u = u"a"
        assert id(self.unwrap_wrap_unicode(u)) == id(u)
        s = "a"
        assert id(self.unwrap_wrap_str(s)) == id(s)
