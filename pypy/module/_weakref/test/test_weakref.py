from pypy.conftest import gettestobjspace

class AppTestWeakref(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_weakref',))
        cls.space = space
                    
    def test_simple(self):
        import _weakref
        class A:
            pass
        a = A()
        ref = _weakref.ref(a)
        print ref()
        assert ref() is a
        del a
        print ref()
        assert ref() is None
