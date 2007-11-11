
# this test isn't so much to test that the objspace interface *works*
# -- it's more to test that it's *there*

class AppTestTraceBackAttributes:

    def test_newstring(self):
        # XXX why is this called newstring?
        import sys
        def f():
            raise TypeError, "hello"

        def g():
            f()
        
        try:
            g()
        except:
            typ,val,tb = sys.exc_info()
        else:
            raise AssertionError, "should have raised"
        assert hasattr(tb, 'tb_frame')
        assert hasattr(tb, 'tb_lasti')
        assert hasattr(tb, 'tb_lineno')
        assert hasattr(tb, 'tb_next')

    def test_descr_dict(self):
        def f():
            pass
        dictdescr = type(f).__dict__['__dict__']   # only for functions
        assert dictdescr.__get__(f) is f.__dict__
        raises(TypeError, dictdescr.__get__, 5)
        d = {}
        dictdescr.__set__(f, d)
        assert f.__dict__ is d
        raises(TypeError, dictdescr.__set__, f, "not a dict")
        raises(TypeError, dictdescr.__set__, 5, d)
        # in PyPy, the following descr applies to any object that has a dict,
        # but not to objects without a dict, obviously
        dictdescr = type.__dict__['__dict__']
        raises(TypeError, dictdescr.__get__, 5)
        raises(TypeError, dictdescr.__set__, 5, d)

    def test_descr_member_descriptor(self):
        class X(object):
            __slots__ = ['x']
        member = X.x
        assert member.__name__ == 'x'
        assert member.__objclass__ is X
        raises((TypeError, AttributeError), "member.__name__ = 'x'")
        raises((TypeError, AttributeError), "member.__objclass__ = X")

    def test_descr_getsetproperty(self):
        from types import FrameType
        assert FrameType.f_lineno.__name__ == 'f_lineno'
        assert FrameType.f_lineno.__objclass__ is FrameType
        class A(object):
            pass
        assert A.__dict__['__dict__'].__name__ == '__dict__'
