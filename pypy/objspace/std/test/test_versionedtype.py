from pypy.objspace.std.test import test_typeobject
from pypy.conftest import gettestobjspace

class TestVersionedType(test_typeobject.TestTypeObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtypeversion": True})

    def get_three_classes(self):
        space = self.space
        w_types = space.appexec([], """():
            class A(object):
                def f(self): pass
            class B(A):
                pass
            class metatype(type):
                pass
            class C(object):
                __metaclass__ = metatype
            return A, B, C
        """)
        return space.unpackiterable(w_types)

    def test_tag_changes(self):
        space = self.space
        w_A, w_B, w_C = self.get_three_classes()
        atag = w_A.version_tag
        btag = w_B.version_tag
        assert atag is not None
        assert btag is not None
        assert w_C.version_tag is None
        assert atag is not btag
        w_types = space.appexec([w_A, w_B], """(A, B):
            B.g = lambda self: None
        """)
        assert w_B.version_tag is not btag
        assert w_A.version_tag is atag
        btag = w_B.version_tag
        w_types = space.appexec([w_A, w_B], """(A, B):
            A.f = lambda self: None
        """)
        assert w_B.version_tag is not btag
        assert w_A.version_tag is not atag
        atag = w_A.version_tag
        btag = w_B.version_tag
        assert atag is not btag
        w_types = space.appexec([w_A, w_B], """(A, B):
            del A.f
        """)
        assert w_B.version_tag is not btag
        assert w_A.version_tag is not atag
        atag = w_A.version_tag
        btag = w_B.version_tag
        assert atag is not btag

    def test_tag_changes_when_bases_change(self):
        space = self.space
        w_A, w_B, w_C = self.get_three_classes()
        atag = w_A.version_tag
        btag = w_B.version_tag
        w_types = space.appexec([w_A, w_B, w_C], """(A, B, C):
            class D(object):
                pass
            B.__bases__ = (D, )
        """)
        assert w_B.version_tag is None

    def test_version_tag_of_builtin_types(self):
        space = self.space
        assert space.w_list.version_tag is not None
        assert space.w_dict.version_tag is not None
        assert space.type(space.sys).version_tag is None
        assert space.w_type.version_tag is None
        w_function = space.appexec([], """():
            def f():
                pass
            return type(f)
        """)
        assert w_function.version_tag is None


class AppTestVersionedType(test_typeobject.AppTestTypeObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtypeversion": True})


