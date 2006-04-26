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
        assert ref() is a
        del a
        assert ref() is None

    def test_callback(self):
        import _weakref
        class A:
            pass
        a1 = A()
        a2 = A()
        def callback(ref):
            a2.ref = ref()
        ref1 = _weakref.ref(a1, callback)
        ref2 = _weakref.ref(a1)
        del a1
        assert ref1() is None
        assert a2.ref is None

    def test_callback_order(self):
        import _weakref
        class A:
            pass
        a1 = A()
        a2 = A()
        def callback1(ref):
            a2.x = 42
        def callback2(ref):
            a2.x = 43
        ref1 = _weakref.ref(a1, callback1)
        ref2 = _weakref.ref(a1, callback2)
        del a1
        assert a2.x == 42
        
