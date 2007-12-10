from pypy.conftest import gettestobjspace

class TestShadowTracking(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withshadowtracking": True})

    def test_simple_shadowing(self):
        space = self.space
        w_inst = space.appexec([], """():
            class A(object):
                def f(self):
                    return 42
            a = A()
            return a
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything()
        space.appexec([w_inst], """(a):
            a.g = "foo"
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything()
        space.appexec([w_inst], """(a):
            a.f = "foo"
        """)
        assert w_inst.w__dict__.implementation.shadows_anything()

    def test_shadowing_via__dict__(self):
        space = self.space
        w_inst = space.appexec([], """():
            class A(object):
                def f(self):
                    return 42
            a = A()
            return a
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything()
        space.appexec([w_inst], """(a):
            a.__dict__["g"] = "foo"
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything()
        space.appexec([w_inst], """(a):
            a.__dict__["f"] = "foo"
        """)
        assert w_inst.w__dict__.implementation.shadows_anything()

    def test_changing__dict__(self):
        space = self.space
        w_inst = space.appexec([], """():
            class A(object):
                def f(self):
                    return 42
            a = A()
            return a
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything()
        space.appexec([w_inst], """(a):
            a.__dict__ = {}
        """)
        assert w_inst.w__dict__.implementation.shadows_anything()

    def test_changing__class__(self):
        space = self.space
        w_inst = space.appexec([], """():
            class A(object):
                def f(self):
                    return 42
            a = A()
            return a
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything()
        space.appexec([w_inst], """(a):
            class B(object):
                def g(self):
                    return 42
            a.__class__ = B
        """)
        assert w_inst.w__dict__.implementation.shadows_anything()

    def test_changing_the_type(self):
        space = self.space
        w_inst = space.appexec([], """():
            class A(object):
                pass
            a = A()
            a.x = 72
            return a
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything()
        w_x = space.appexec([w_inst], """(a):
            a.__class__.x = 42
            return a.x
        """)
        assert space.unwrap(w_x) == 72
        assert w_inst.w__dict__.implementation.shadows_anything()

class AppTestShadowTracking(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withshadowtracking": True})

    def test_shadowtracking_does_not_blow_up(self):
        class A(object):
            def f(self):
                return 42
        a = A()
        assert a.f() == 42
        a.f = lambda : 43
        assert a.f() == 43

class AppTestMethodCaching(AppTestShadowTracking):
    def setup_class(cls):
        cls.space = gettestobjspace(
            **{"objspace.std.withmethodcachecounter": True})

    def test_mix_classes(self):
        import __pypy__
        class A(object):
            def f(self):
                return 42
        class B(object):
            def f(self):
                return 43
        class C(object):
            def f(self):
                return 44
        l = [A(), B(), C()] * 10
        __pypy__.reset_method_cache_counter()
        for i, a in enumerate(l):
            assert a.f() == 42 + i % 3
        cache_counter = __pypy__.method_cache_counter("f")
        assert cache_counter[0] >= 15
        assert cache_counter[1] >= 3 # should be (27, 3)
        assert sum(cache_counter) == 30

    def test_class_that_cannot_be_cached(self):
        import __pypy__
        class metatype(type):
            pass
        class A(object):
            __metaclass__ = metatype
            def f(self):
                return 42

        class B(object):
            def f(self):
                return 43
        class C(object):
            def f(self):
                return 44
        l = [A(), B(), C()] * 10
        __pypy__.reset_method_cache_counter()
        for i, a in enumerate(l):
            assert a.f() == 42 + i % 3
        cache_counter = __pypy__.method_cache_counter("f")
        assert cache_counter[0] >= 9
        assert cache_counter[1] >= 2 # should be (18, 2)
        assert sum(cache_counter) == 20
 
    def test_change_methods(self):
        import __pypy__
        class A(object):
            def f(self):
                return 42
        l = [A()] * 10
        __pypy__.reset_method_cache_counter()
        for i, a in enumerate(l):
            assert a.f() == 42 + i
            A.f = eval("lambda self: %s" % (42 + i + 1, ))
        cache_counter = __pypy__.method_cache_counter("f")
        assert cache_counter == (0, 10)

    def test_subclasses(self):
        import __pypy__
        class A(object):
            def f(self):
                return 42
        class B(object):
            def f(self):
                return 43
        class C(A):
            pass
        l = [A(), B(), C()] * 10
        __pypy__.reset_method_cache_counter()
        for i, a in enumerate(l):
            assert a.f() == 42 + (i % 3 == 1)
        cache_counter = __pypy__.method_cache_counter("f")
        assert cache_counter[0] >= 15
        assert cache_counter[1] >= 3 # should be (27, 3)
        assert sum(cache_counter) == 30
  
    def test_many_names(self):
        import __pypy__
        class A(object):
            foo = 5
            bar = 6
            baz = 7
            xyz = 8
            stuff = 9
            a = 10
            foobar = 11

        a = A()
        names = [name for name in A.__dict__.keys()
                      if not name.startswith('_')]
        names_repeated = names * 10
        result = []
        __pypy__.reset_method_cache_counter()
        for name in names_repeated:
            result.append(getattr(a, name))
        append_counter = __pypy__.method_cache_counter("append")
        names_counters = [__pypy__.method_cache_counter(name)
                          for name in names]
        assert append_counter[0] >= 5 * len(names)
        for name, count in zip(names, names_counters):
            assert count[0] >= 5

    def test_mutating_bases(self):
        class C(object):
            pass
        class C2(object):
            foo = 5
        class D(C):
            pass
        class E(D):
            pass
        d = D()
        e = E()
        D.__bases__ = (C2,)
        assert e.foo == 5

        class F(object):
            foo = 3
        D.__bases__ = (C, F)
        assert e.foo == 3
