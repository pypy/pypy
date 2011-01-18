from pypy.objspace.std.smalltupleobject import W_SmallTupleObject
from pypy.interpreter.error import OperationError
from pypy.objspace.std.test.test_tupleobject import AppTestW_TupleObject
from pypy.conftest import gettestobjspace

class AppTestW_SmallTupleObject(AppTestW_TupleObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsmalltuple": True})
        cls.w_issmall = cls.space.appexec([], """():
            import __pypy__
            def issmall(obj):
                assert "SmallTuple" in __pypy__.internal_repr(obj)
            return issmall
        """)

    def test_slicing_to_small(self):
        self.issmall((1, 2, 3)[0:2])
        self.issmall((1, 2, 3)[0:2:1])

    def test_adding_to_small(self):
        self.issmall((1,)+(2,))

    def test_multiply_to_small(self):
        self.issmall((1,)*2)

    def test_slicing_from_small(self):
        assert (1,2)[0:1:1] == (1,)

class TestW_SmallTupleObject():

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsmalltuple": True})

    def test_issmalltupleobject(self):
        w_tuple = self.space.newtuple([self.space.wrap(1), self.space.wrap(2)])
        assert isinstance(w_tuple, W_SmallTupleObject)
