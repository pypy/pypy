from pypy.conftest import gettestobjspace
from pypy.objspace.std.test.test_typeobject import AppTestTypeObject


class AppTestMethodCaching(AppTestTypeObject):
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
        class X:
            pass
        class Y(object):
            pass
        class A(Y, X):
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
        # the cache hits come from A.f = ..., which first does a lookup on A as
        # well
        assert cache_counter == (17, 3)

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
        names.sort()
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
            assert count[0] >= 5, str((name, count))

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

    def test_custom_metaclass(self):
        import __pypy__
        class MetaA(type):
            def __getattribute__(self, x):
                return 1
        def f(self):
            return 42
        A = type.__new__(MetaA, "A", (), {"f": f})
        l = [type.__getattribute__(A, "__new__")(A)] * 10
        __pypy__.reset_method_cache_counter()
        for i, a in enumerate(l):
            assert a.f() == 42
        cache_counter = __pypy__.method_cache_counter("f")
        assert cache_counter[0] >= 5
        assert cache_counter[1] >= 1 # should be (27, 3)
        assert sum(cache_counter) == 10

    def test_mutate_class(self):
        import __pypy__
        class A(object):
            x = 1
            y = 2
        __pypy__.reset_method_cache_counter()
        a = A()
        for i in range(100):
            assert a.y == 2
            assert a.x == i + 1
            A.x += 1
        cache_counter = __pypy__.method_cache_counter("x")
        assert cache_counter[0] >= 350
        assert cache_counter[1] >= 1
        assert sum(cache_counter) == 400

        __pypy__.reset_method_cache_counter()
        a = A()
        for i in range(100):
            assert a.y == 2
            setattr(a, "a%s" % i, i)
        cache_counter = __pypy__.method_cache_counter("x")
        assert cache_counter[0] == 0 # 0 hits, because all the attributes are new

    def test_get_module_from_namedtuple(self):
        # this used to crash
        from collections import namedtuple
        assert namedtuple("a", "b").__module__
