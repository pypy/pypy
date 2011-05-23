import py
from pypy.conftest import gettestobjspace, option

class AppTest(object):
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("does not make sense on pypy-c")
        cls.space = gettestobjspace(**{"objspace.usemodules.select": False})

    def test__isfake(self):
        from __pypy__ import isfake
        assert not isfake(map)
        assert not isfake(object)
        assert not isfake(isfake)

    def test__isfake_currently_true(self):
        from __pypy__ import isfake
        import select
        assert isfake(select)

    def test_cpumodel(self):
        import __pypy__
        assert hasattr(__pypy__, 'cpumodel')

    def test_builtinify(self):
        import __pypy__
        class A(object):
            a = lambda *args: args
            b = __pypy__.builtinify(a)
        my = A()
        assert my.a() == (my,)
        assert my.b() == ()
        assert A.a(my) == (my,)
        assert A.b(my) == (my,)
        assert A.a.im_func(my) == (my,)
        assert not hasattr(A.b, 'im_func')
        assert A.a is not A.__dict__['a']
        assert A.b is A.__dict__['b']

    def test_lookup_special(self):
        from __pypy__ import lookup_special
        class X(object):
            def foo(self): return 42
        x = X()
        x.foo = 23
        assert lookup_special(x, "foo")() == 42
        class X:
            pass
        raises(TypeError, lookup_special, X(), "foo")
