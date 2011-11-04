import py
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.specialisedtupleobject import W_SpecialisedTupleObject,W_SpecialisedTupleObjectIntInt
from pypy.interpreter.error import OperationError
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test.test_tupleobject import AppTestW_TupleObject



class TestW_SpecialisedTupleObject():

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})

    def test_isspecialisedtupleobjectintint(self):
        py.test.skip('in progress')
        w_tuple = self.space.newtuple([self.space.wrap(1), self.space.wrap(2)])
        assert isinstance(w_tuple, W_SpecialisedTupleObjectIntInt)
        
    def test_isnotspecialisedtupleobject(self):
        w_tuple = self.space.newtuple([self.space.wrap({})])
        assert not isinstance(w_tuple, W_SpecialisedTupleObject)
        
    def test_hash_against_normal_tuple(self):
        py.test.skip('in progress')
        normalspace = gettestobjspace(**{"objspace.std.withspecialisedtuple": False})
        w_tuple = normalspace.newtuple([self.space.wrap(1)])

        specialisedspace = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})
        w_specialisedtuple = specialisedspace.newtuple([self.space.wrap(1)])

        assert isinstance(w_specialisedtuple, W_SpecialisedTupleObject)
        assert isinstance(w_tuple, W_TupleObject)
        assert not normalspace.is_true(normalspace.eq(w_tuple, w_specialisedtuple))
        assert specialisedspace.is_true(specialisedspace.eq(w_tuple, w_specialisedtuple))
        assert specialisedspace.is_true(specialisedspace.eq(normalspace.hash(w_tuple), specialisedspace.hash(w_specialisedtuple)))

    def test_setitem(self):
        py.test.skip('in progress')
        w_specialisedtuple = self.space.newtuple([self.space.wrap(1)])
        w_specialisedtuple.setitem(0, self.space.wrap(5))
        list_w = w_specialisedtuple.tolist()
        assert len(list_w) == 1
        assert self.space.eq_w(list_w[0], self.space.wrap(5))        

class AppTestW_SpecialisedTupleObject(AppTestW_TupleObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})
        cls.w_isspecialised = cls.space.appexec([], """():
            import __pypy__
            def isspecialised(obj):
                return "SpecialisedTuple" in __pypy__.internal_repr(obj)
            return isspecialised
        """)

    def test_specialisedtuple(self):
        skip('in progress')
        assert self.isspecialised((42,43))

    def test_notspecialisedtuple(self):
        skip('in progress')
        assert not self.isspecialised((42,43,44))
        
    def test_slicing_to_specialised(self):
        skip('in progress')
        assert self.isspecialised((1, 2, 3)[0:1])   
        assert self.isspecialised((1, '2', 1.3)[0:5:5])
        assert self.isspecialised((1, '2', 1.3)[1:5:5])
        assert self.isspecialised((1, '2', 1.3)[2:5:5])

    def test_adding_to_specialised(self):
        skip('in progress')
        assert self.isspecialised((1,)+(2,))

    def test_multiply_to_specialised(self):
        skip('in progress')
        assert self.isspecialised((1,)*2)

    def test_slicing_from_specialised(self):
        skip('in progress')
        assert (1,2,3)[0:2:1] == (1,)

    def test_eq(self):
        skip('in progress')
        a = (1,2)
        b = (1,2)
        assert a == b

        c = (1,3,2)
        assert a != c

    def test_hash(self):
        skip('in progress')
        a = (1,)
        b = (1,)
        assert hash(a) == hash(b)

        a = ('1',)
        b = ('1',)
        assert hash(a) == hash(b)

        a = (1.1,)
        b = (1.1,)
        assert hash(a) == hash(b)

        c = (2,)
        assert hash(a) != hash(c)

        
        
        
        
        
