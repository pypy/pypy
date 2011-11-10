import py
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.specialisedtupleobject import W_SpecialisedTupleObject,W_SpecialisedTupleObjectIntInt
from pypy.interpreter.error import OperationError
from pypy.conftest import gettestobjspace
from pypy.objspace.std.test.test_tupleobject import AppTestW_TupleObject
from pypy.interpreter import gateway


class TestW_SpecialisedTupleObject():

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})

    def test_isspecialisedtupleobjectintint(self):
        w_tuple = self.space.newtuple([self.space.wrap(1), self.space.wrap(2)])
        assert isinstance(w_tuple, W_SpecialisedTupleObjectIntInt)
        
    def test_isnotspecialisedtupleobject(self):
        w_tuple = self.space.newtuple([self.space.wrap({})])
        assert not isinstance(w_tuple, W_SpecialisedTupleObject)
        
    def test_specialisedtupleclassname(self):
        w_tuple = self.space.newtuple([self.space.wrap(1), self.space.wrap(2)])
        assert w_tuple.__class__.__name__ == 'W_SpecialisedTupleObjectIntInt'
            
    def test_hash_against_normal_tuple(self):
        N_space = gettestobjspace(**{"objspace.std.withspecialisedtuple": False})
        S_space = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})
        
        def hash_test(values):
            N_values_w = [N_space.wrap(value) for value in values]
            S_values_w = [S_space.wrap(value) for value in values]
            N_w_tuple = N_space.newtuple(N_values_w)
            S_w_tuple = S_space.newtuple(S_values_w)
    
            assert isinstance(S_w_tuple, W_SpecialisedTupleObject)
            assert isinstance(N_w_tuple, W_TupleObject)
            assert not N_space.is_true(N_space.eq(N_w_tuple, S_w_tuple))
            assert S_space.is_true(S_space.eq(N_w_tuple, S_w_tuple))
            assert S_space.is_true(S_space.eq(N_space.hash(N_w_tuple), S_space.hash(S_w_tuple)))

        hash_test([1,2])
        hash_test([1.5,2.8])
        hash_test([1.0,2.0])
        hash_test(['arbitrary','strings'])
        hash_test([1,(1,2,3,4)])
        hash_test([1,(1,2)])
        hash_test([1,('a',2)])
        hash_test([1,()])
        
    def test_setitem(self):
        py.test.skip('skip for now, only needed for cpyext')
        w_specialisedtuple = self.space.newtuple([self.space.wrap(1)])
        w_specialisedtuple.setitem(0, self.space.wrap(5))
        list_w = w_specialisedtuple.tolist()
        assert len(list_w) == 1
        assert self.space.eq_w(list_w[0], self.space.wrap(5))        

class AppTestW_SpecialisedTupleObject(AppTestW_TupleObject):

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})
        def forbid_delegation(space, w_tuple):
            def delegation_forbidden():
                raise NotImplementedError
            w_tuple.tolist = delegation_forbidden
            return w_tuple
        cls.w_forbid_delegation = cls.space.wrap(gateway.interp2app(forbid_delegation))
            
    def w_isspecialised(self, obj):
       import __pypy__
       return "SpecialisedTuple" in __pypy__.internal_repr(obj)
       

    def test_createspecialisedtuple(self):
        assert self.isspecialised((42,43))
        assert self.isspecialised((4.2,4.3))
        assert self.isspecialised((1.0,2.0))
        assert self.isspecialised(('a','b'))
        
    def test_len(self):
        t = self.forbid_delegation((42,43))
        assert len(t) == 2

    def test_notspecialisedtuple(self):
        assert not self.isspecialised((42,43,44,45))
        assert not self.isspecialised((1.5,2))
        assert not self.isspecialised((1.0,2))

    def test_slicing_to_specialised(self):
        assert self.isspecialised((1, 2, 3)[0:2])   
        assert self.isspecialised((1, '2', 3)[0:5:2])

    def test_adding_to_specialised(self):
        assert self.isspecialised((1,)+(2,))

    def test_multiply_to_specialised(self):
        assert self.isspecialised((1,)*2)

    def test_slicing_from_specialised(self):
        assert (1,2,3)[0:2:1] == (1,2)

    def test_eq_no_delegation(self):
        a = self.forbid_delegation((1,2))
        b = (1,2)
        assert a == b
        
        c = (2,1)
        assert not a == c
                
    def test_eq_can_delegate(self):        
        a = (1,2)
        b = (1,3,2)
        assert not a == b
         
        values = [2, 2L, 2.0, 1, 1L, 1.0]
        for x in values:
            for y in values:
                assert ((1,2) == (x,y)) == (1 == x and 2 == y)

    def test_neq(self):
        a = self.forbid_delegation((1,2))
        b = (1,)
        b = b+(2,)
        assert not a != b
        
        c = (1,3)
        assert a != c
        
    def test_ordering(self):
        a = self.forbid_delegation((1,2))
        assert a <  (2,2)    
        assert a <  (1,3)    
        assert not a <  (1,2) 
           
        assert a <=  (2,2)    
        assert a <=  (1,2) 
        assert not a <=  (1,1) 
           
        assert a >= (0,2)    
        assert a >= (1,2)    
        assert not a >= (1,3)    
        
        assert a > (0,2)    
        assert a > (1,1)    
        assert not a > (1,3)    
        
    def test_hash(self):
        a = (1,2)
        b = (1,) + (2,) # else a and b refer to same constant
        assert hash(a) == hash(b)

        c = (2,4)
        assert hash(a) != hash(c)

    def test_getitem(self):
        t = self.forbid_delegation((5,3))
        assert (t)[0] == 5
        assert (t)[1] == 3
        assert (t)[-1] == 3
        assert (t)[-2] == 5
        raises(IndexError, "t[2]")
        
    def test_three_tuples(self):
        if not self.isspecialised((1,2,3)):
            skip('3-tuples of ints are not specialised, so skip specific tests on them')
        b = self.forbid_delegation((1,2,3))
        c = (1,)
        d = c + (2,3)
        assert self.isspecialised(d)
        assert b == d
        assert b <= d
        
    def test_mongrel(self):
        a = self.forbid_delegation((1, 2.2, '333'))
        if not self.isspecialised(a):
            skip('my chosen kind of mixed type tuple is not specialised, so skip specific tests on them')
        assert len(a) == 3
        assert a[0] == 1 and a[1] == 2.2 and a[2] == '333'
        assert a == (1,) + (2.2,) + ('333',)
        assert a < (1, 2.2, '334')
        
    def test_mongrel_with_any(self):
        a = self.forbid_delegation((1, 2.2, '333',[]))
        b = (1, 2.2) + ('333', [])
        if not self.isspecialised(a):
            skip('my chosen kind of mixed type tuple is not specialised, so skip specific tests on them')
        assert len(a) == 4
        assert a[0] == 1 and a[1] == 2.2 and a[2] == '333' and a[3] == []
        assert a != (1, 2.2, '334', [])
#        assert b == a
#        assert a == (1,) + (2.2,) + ('333',) + ([],)
#        assert a < (1, 2.2, '334', {})
