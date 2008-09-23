from pypy.conftest import gettestobjspace

class AppTestWeakref(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_weakref',))
        cls.space = space
                    
    def test_simple(self):
        import _weakref, gc
        class A(object):
            pass
        a = A()
        assert _weakref.getweakrefcount(a) == 0
        ref = _weakref.ref(a)
        assert ref() is a
        assert a.__weakref__ is ref
        assert _weakref.getweakrefcount(a) == 1
        del a
        gc.collect()
        assert ref() is None

    def test_callback(self):
        import _weakref, gc
        class A(object):
            pass
        a1 = A()
        a2 = A()
        def callback(ref):
            a2.ref = ref()
        ref1 = _weakref.ref(a1, callback)
        ref2 = _weakref.ref(a1)
        assert _weakref.getweakrefcount(a1) == 2
        del a1
        gc.collect()
        assert ref1() is None
        assert a2.ref is None

    def test_callback_order(self):
        import _weakref, gc
        class A(object):
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
        gc.collect()
        assert a2.x == 42
        
    def test_dont_callback_if_weakref_dead(self):
        import _weakref, gc
        class A(object):
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
        gc.collect()
        assert _weakref.getweakrefcount(a2) == 0
        a2 = None
        gc.collect()
        assert a1.x == 40

    def test_callback_cannot_ressurect(self):
        import _weakref, gc
        class A(object):
            pass
        a = A()
        alive = A()
        alive.a = 1
        def callback(ref2):
            alive.a = ref1()
        ref1 = _weakref.ref(a, callback)
        ref2 = _weakref.ref(a, callback)
        del a
        gc.collect()
        assert alive.a is None

    def test_weakref_reusing(self):
        import _weakref, gc
        class A(object):
            pass
        a = A()
        ref1 = _weakref.ref(a)
        ref2 = _weakref.ref(a)
        assert ref1 is ref2
        class wref(_weakref.ref):
            pass
        wref1 = wref(a)
        assert isinstance(wref1, wref)

    def test_correct_weakrefcount_after_death(self):
        import _weakref, gc
        class A(object):
            pass
        a = A()
        ref1 = _weakref.ref(a)
        ref2 = _weakref.ref(a)
        assert _weakref.getweakrefcount(a) == 1
        del ref1
        gc.collect()
        assert _weakref.getweakrefcount(a) == 1
        del ref2
        gc.collect()
        assert _weakref.getweakrefcount(a) == 0

    def test_weakref_equality(self):
        import _weakref, gc
        class A(object):
            def __eq__(self, other):
                return True
        a1 = A()
        a2 = A()
        ref1 = _weakref.ref(a1)
        ref2 = _weakref.ref(a2)
        assert ref1 == ref2
        del a1
        gc.collect()
        assert not ref1 == ref2
        assert ref1 != ref2
        del a2
        gc.collect()
        assert not ref1 == ref2
        assert ref1 != ref2

    def test_getweakrefs(self):
        import _weakref, gc
        class A(object):
            pass
        a = A()
        assert _weakref.getweakrefs(a) == []
        assert _weakref.getweakrefs(None) == []
        ref1 = _weakref.ref(a)
        assert _weakref.getweakrefs(a) == [ref1]

    def test_hashing(self):
        import _weakref, gc
        class A(object):
            def __hash__(self):
                return 42
        a = A()
        w = _weakref.ref(a)
        assert hash(a) == hash(w)
        del a
        gc.collect()
        assert hash(w) == 42
        w = _weakref.ref(A())
        gc.collect()
        raises(TypeError, hash, w)

    def test_weakref_subclassing(self):
        import _weakref, gc
        class A(object):
            pass
        class Ref(_weakref.ref):
            pass
        def callable(ref):
            b.a = 42
        a = A()
        b = A()
        b.a = 1
        w = Ref(a, callable)
        assert a.__weakref__ is w
        assert b.__weakref__ is None
        w1 = _weakref.ref(a)
        w2 = _weakref.ref(a, callable)
        assert a.__weakref__ is w1
        del a
        gc.collect()
        assert w1() is None
        assert w() is None
        assert w2() is None
        assert b.a == 42

    def test_function_weakrefable(self):
        import _weakref, gc
        def f(x):
            return 42
        wf = _weakref.ref(f)
        assert wf()(63) == 42
        del f
        gc.collect()
        assert wf() is None

    def test_method_weakrefable(self):
        import _weakref, gc
        class A(object):
            def f(self):
                return 42
        a = A()
        meth = A.f
        w_unbound = _weakref.ref(meth)
        assert w_unbound()(A()) == 42
        meth = A().f
        w_bound = _weakref.ref(meth)
        assert w_bound()() == 42
        del meth
        gc.collect()
        assert w_unbound() is None
        assert w_bound() is None

    def test_set_weakrefable(self):
        import _weakref, gc
        s = set([1, 2, 3, 4])
        w = _weakref.ref(s)
        assert w() is s
        del s
        gc.collect()
        assert w() is None

    def test_generator_weakrefable(self):
        import _weakref, gc
        def f(x):
            for i in range(x):
                yield i
        g = f(10)
        w = _weakref.ref(g)
        r = w().next()
        assert r == 0
        r = g.next()
        assert r == 1
        del g
        gc.collect()
        assert w() is None

    def test_weakref_subclass_with_del(self):
        import _weakref, gc
        class Ref(_weakref.ref):
            def __del__(self):
                b.a = 42
        class A(object):
            pass
        a = A()
        b = A()
        b.a = 1
        w = Ref(a)
        del w
        gc.collect()
        assert b.a == 42
        if _weakref.getweakrefcount(a) > 0:
            # the following can crash if the presence of the applevel __del__
            # leads to the fact that the __del__ of _weakref.ref is not called.
            assert _weakref.getweakrefs(a)[0]() is a

    def test_buggy_case(self):
        import gc, weakref
        gone = []
        class A(object):
            def __del__(self):
                gone.append(True)
        a = A()
        w = weakref.ref(a)
        del a
        tries = 5
        for i in range(5):
            if not gone:
                gc.collect()
        if gone:
            a1 = w()
            assert a1 is None

    def test_del_and_callback_and_id(self):
        import gc, weakref
        seen_del = []
        class A(object):
            def __del__(self):
                seen_del.append(id(self))
                seen_del.append(w1() is None)
                seen_del.append(w2() is None)
        seen_callback = []
        def callback(r):
            seen_callback.append(r is w2)
            seen_callback.append(w1() is None)
            seen_callback.append(w2() is None)
        a = A()
        w1 = weakref.ref(a)
        w2 = weakref.ref(a, callback)
        aid = id(a)
        del a
        for i in range(5):
            gc.collect()
        if seen_del:
            assert seen_del == [aid, True, True]
        if seen_callback:
            assert seen_callback == [True, True, True]


class AppTestProxy(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_weakref',))
        cls.space = space
                    
    def test_simple(self):
        import _weakref, gc
        class A(object):
            def __init__(self, x):
                self.x = x
        a = A(1)
        p = _weakref.proxy(a)
        assert p.x == 1
        assert str(p) == str(a)
        raises(TypeError, p)

    def test_caching(self):
        import _weakref, gc
        class A(object): pass
        a = A()
        assert _weakref.proxy(a) is _weakref.proxy(a)

    def test_callable_proxy(self):
        import _weakref, gc
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

    def test_callable_proxy_type(self):
        import _weakref, gc
        class Callable(object):
            def __call__(self, x):
                pass
        o = Callable()
        ref1 = _weakref.proxy(o)
        assert type(ref1) is _weakref.CallableProxyType

    def test_dont_create_directly(self):
        import _weakref, gc
        raises(TypeError, _weakref.ProxyType, [])
        raises(TypeError, _weakref.CallableProxyType, [])

    def test_dont_hash(self):
        import _weakref, gc
        class A(object):
            pass
        a = A()
        p = _weakref.proxy(a)
        raises(TypeError, hash, p)

    def test_subclassing_not_allowed(self):
        import _weakref, gc
        def tryit():
            class A(_weakref.ProxyType):
                pass
            return A
        raises(TypeError, tryit)

    def test_repr(self):
        import _weakref, gc
        for kind in ('ref', 'proxy'):
            def foobaz():
                "A random function not returning None."
                return 42
            w = getattr(_weakref, kind)(foobaz)
            s = repr(w)
            print s
            if kind == 'ref':
                assert s.startswith('<weakref at ')
            else:
                assert (s.startswith('<weakproxy at ') or
                        s.startswith('<weakcallableproxy at '))
            assert "function" in s
            del foobaz
            try:
                for i in range(10):
                    if w() is None:
                        break     # only reachable if kind == 'ref'
                    gc.collect()
            except ReferenceError:
                pass    # only reachable if kind == 'proxy'
            s = repr(w)
            print s
            assert "dead" in s

    def test_eq(self):
        import _weakref
        class A(object):
            pass

        a = A()
        assert not(_weakref.ref(a) == a)
        assert _weakref.ref(a) != a

        class A(object):
            def __eq__(self, other):
                return True

        a = A()
        assert _weakref.ref(a) == a
    
