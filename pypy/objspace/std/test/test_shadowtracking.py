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
        assert not w_inst.w__dict__.implementation.shadows_anything
        space.appexec([w_inst], """(a):
            a.g = "foo"
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything
        space.appexec([w_inst], """(a):
            a.f = "foo"
        """)
        assert w_inst.w__dict__.implementation.shadows_anything

    def test_shadowing_via__dict__(self):
        space = self.space
        w_inst = space.appexec([], """():
            class A(object):
                def f(self):
                    return 42
            a = A()
            return a
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything
        space.appexec([w_inst], """(a):
            a.__dict__["g"] = "foo"
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything
        space.appexec([w_inst], """(a):
            a.__dict__["f"] = "foo"
        """)
        assert w_inst.w__dict__.implementation.shadows_anything

    def test_changing__dict__(self):
        space = self.space
        w_inst = space.appexec([], """():
            class A(object):
                def f(self):
                    return 42
            a = A()
            return a
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything
        space.appexec([w_inst], """(a):
            a.__dict__ = {}
        """)
        assert w_inst.w__dict__.implementation.shadows_anything

    def test_changing__class__(self):
        space = self.space
        w_inst = space.appexec([], """():
            class A(object):
                def f(self):
                    return 42
            a = A()
            return a
        """)
        assert not w_inst.w__dict__.implementation.shadows_anything
        space.appexec([w_inst], """(a):
            class B(object):
                def g(self):
                    return 42
            a.__class__ = B
        """)
        assert w_inst.w__dict__.implementation.shadows_anything

