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
        assert _weakref.getweakrefcount(a) == 0
        ref = _weakref.ref(a)
        assert ref() is a
        assert _weakref.getweakrefcount(a) == 1
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
        assert _weakref.getweakrefcount(a1) == 2
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
        
    def test_dont_callback_if_weakref_dead(self):
        import _weakref
        class A:
            pass
        a1 = A()
        a1.x = 40
        a2 = A()
        def callback(ref):
            a1.x = 42
        assert _weakref.getweakrefcount(a2) == 0
        ref = _weakref.ref(a2, callback)
        assert _weakref.getweakrefcount(a2) == 1
        ref = None
        assert _weakref.getweakrefcount(a2) == 0
        a2 = None
        assert a1.x == 40

    def test_callback_cannot_ressurect(self):
        import _weakref
        class A:
            pass
        a = A()
        alive = A()
        alive.a = 1
        def callback(ref2):
            alive.a = ref1()
        ref1 = _weakref.ref(a, callback)
        ref2 = _weakref.ref(a, callback)
        del a
        assert alive.a is None

    def test_weakref_reusing(self):
        import _weakref
        class A:
            pass
        a = A()
        ref1 = _weakref.ref(a)
        ref2 = _weakref.ref(a)
        assert ref1 is ref2
        class wref(_weakref.ref):
            pass
        wref1 = wref(a)
        assert isinstance(wref1, wref)

    def test_weakref_equality(self):
        import _weakref
        class A:
            def __eq__(self, other):
                return True
        a1 = A()
        a2 = A()
        ref1 = _weakref.ref(a1)
        ref2 = _weakref.ref(a2)
        assert ref1 == ref2
        del a1
        assert not ref1 == ref2
        assert ref1 != ref2
        del a2
        assert not ref1 == ref2
        assert ref1 != ref2

    def test_getweakrefs(self):
        import _weakref
        class A:
            pass
        a = A()
        assert _weakref.getweakrefs(a) == []
        assert _weakref.getweakrefs(None) == []
        ref1 = _weakref.ref(a)
        assert _weakref.getweakrefs(a) == [ref1]

    def test_hashing(self):
        import _weakref
        class A(object):
            def __hash__(self):
                return 42
        a = A()
        w = _weakref.ref(a)
        assert hash(a) == hash(w)
        del a
        assert hash(w) == 42
        w = _weakref.ref(A())
        raises(TypeError, hash, w)

class AppTestProxy(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_weakref',))
        cls.space = space
                    
    def test_simple(self):
        import _weakref
        class A(object):
            def __init__(self, x):
                self.x = x
        a = A(1)
        p = _weakref.proxy(a)
        assert p.x == 1
        assert str(p) == str(a)
        raises(TypeError, p)

    def test_caching(self):
        import _weakref
        class A(object): pass
        a = A()
        assert _weakref.proxy(a) is _weakref.proxy(a)

    def test_callable_proxy(self):
        import _weakref
        class A(object):
            def __call__(self):
                global_a.x = 1
        global_a = A()
        global_a.x = 41
        A_ = _weakref.proxy(A)
        a = A_()
        assert isinstance(a, A)
        a_ = _weakref.proxy(a)
        a_()
        assert global_a.x == 1

    def test_dont_create_directly(self):
        import _weakref
        raises(TypeError, _weakref.ProxyType, [])
        raises(TypeError, _weakref.CallableProxyType, [])

    def test_dont_hash(self):
        import _weakref
        class A(object):
            pass
        a = A()
        p = _weakref.proxy(a)
        raises(TypeError, hash, p)

    def test_subclassing_not_allowed(self):
        import _weakref
        def tryit():
            class A(_weakref.ProxyType):
                pass
            return A
        raises(TypeError, tryit)
