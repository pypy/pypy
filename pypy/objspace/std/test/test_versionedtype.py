from pypy.objspace.std.test import test_typeobject
from pypy.conftest import gettestobjspace

class TestVersionedType(test_typeobject.TestTypeObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtypeversion": True})

    def test_tag_changes(self):
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
        w_A, w_B, w_C = space.unpackiterable(w_types)
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


class AppTestVersionedType(test_typeobject.AppTestTypeObject):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtypeversion": True})


