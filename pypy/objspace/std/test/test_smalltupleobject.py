from pypy.objspace.std.tupleobject import W_TupleObject
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

    def test_smalltuple(self):
        self.issmall((1,2))
        self.issmall((1,2,3))

    def test_slicing_to_small(self):
        self.issmall((1, 2, 3)[0:2])    # SmallTuple2
        self.issmall((1, 2, 3)[0:2:1])

        self.issmall((1, 2, 3, 4)[0:3])    # SmallTuple3
        self.issmall((1, 2, 3, 4)[0:3:1])

    def test_adding_to_small(self):
        self.issmall((1,)+(2,))       # SmallTuple2
        self.issmall((1,1)+(2,))      # SmallTuple3
        self.issmall((1,)+(2,3))

    def test_multiply_to_small(self):
        self.issmall((1,)*2)
        self.issmall((1,)*3)

    def test_slicing_from_small(self):
        assert (1,2)[0:1:1] == (1,)
        assert (1,2,3)[0:2:1] == (1,2)

    def test_eq(self):
        a = (1,2,3)
        b = (1,2,3)
        assert a == b

        c = (1,3,2)
        assert a != c

    def test_hash(self):
        a = (1,2,3)
        b = (1,2,3)
        assert hash(a) == hash(b)

        c = (1,3,2)
        assert hash(a) != hash(c)

class TestW_SmallTupleObject():

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withsmalltuple": True})

    def test_issmalltupleobject(self):
        w_tuple = self.space.newtuple([self.space.wrap(1), self.space.wrap(2)])
        assert isinstance(w_tuple, W_SmallTupleObject)

    def test_hash_agains_normal_tuple(self):
        normalspace = gettestobjspace(**{"objspace.std.withsmalltuple": False})
        w_tuple = normalspace.newtuple([self.space.wrap(1), self.space.wrap(2)])

        smallspace = gettestobjspace(**{"objspace.std.withsmalltuple": True})
        w_smalltuple = smallspace.newtuple([self.space.wrap(1), self.space.wrap(2)])

        assert isinstance(w_smalltuple, W_SmallTupleObject)
        assert isinstance(w_tuple, W_TupleObject)
        assert not normalspace.is_true(normalspace.eq(w_tuple, w_smalltuple))
        assert smallspace.is_true(smallspace.eq(w_tuple, w_smalltuple))
        assert smallspace.is_true(smallspace.eq(normalspace.hash(w_tuple), smallspace.hash(w_smalltuple)))

    def test_setitem(self):
        w_smalltuple = self.space.newtuple([self.space.wrap(1), self.space.wrap(2)])
        w_smalltuple.setitem(0, self.space.wrap(5))
        list_w = w_smalltuple.tolist()
        assert len(list_w) == 2
        assert self.space.eq_w(list_w[0], self.space.wrap(5))
        assert self.space.eq_w(list_w[1], self.space.wrap(2))
