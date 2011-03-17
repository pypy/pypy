from __future__ import with_statement
from pypy.conftest import option

class AppTestObject:

    def setup_class(cls):
        import sys
        cpython_behavior = (not option.runappdirect
                            or not hasattr(sys, 'pypy_translation_info'))

        cls.w_cpython_behavior = cls.space.wrap(cpython_behavior)
        cls.w_cpython_version = cls.space.wrap(tuple(sys.version_info))

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
