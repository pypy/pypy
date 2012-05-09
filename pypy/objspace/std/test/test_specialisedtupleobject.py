import py, sys
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.specialisedtupleobject import W_SpecialisedTupleObject
from pypy.objspace.std.specialisedtupleobject import _specialisations
from pypy.interpreter.error import OperationError
from pypy.conftest import gettestobjspace, option
from pypy.objspace.std.test import test_tupleobject
from pypy.interpreter import gateway


for cls in _specialisations:
    globals()[cls.__name__] = cls


class TestW_SpecialisedTupleObject():

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})

    def test_isspecialisedtupleobjectintint(self):
        w_tuple = self.space.newtuple([self.space.wrap(1), self.space.wrap(2)])
        assert isinstance(w_tuple, W_SpecialisedTupleObject_ii)
        
    def test_isnotspecialisedtupleobject(self):
        w_tuple = self.space.newtuple([self.space.wrap({})])
        assert not isinstance(w_tuple, W_SpecialisedTupleObject)
        
    def test_specialisedtupleclassname(self):
        w_tuple = self.space.newtuple([self.space.wrap(1), self.space.wrap(2)])
        assert w_tuple.__class__.__name__ == 'W_SpecialisedTupleObject_ii'

    def test_hash_against_normal_tuple(self):
        N_space = gettestobjspace(**{"objspace.std.withspecialisedtuple": False})
        S_space = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})
        
        def hash_test(values, must_be_specialized=True):
            N_values_w = [N_space.wrap(value) for value in values]
            S_values_w = [S_space.wrap(value) for value in values]
            N_w_tuple = N_space.newtuple(N_values_w)
            S_w_tuple = S_space.newtuple(S_values_w)

            if must_be_specialized:
                assert isinstance(S_w_tuple, W_SpecialisedTupleObject)
            assert isinstance(N_w_tuple, W_TupleObject)
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
        hash_test([1,2,3], must_be_specialized=False)


class AppTestW_SpecialisedTupleObject:

    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withspecialisedtuple": True})
        def forbid_delegation(space, w_tuple):
            def delegation_forbidden():
                # haaaack
                co = sys._getframe(2).f_code
                if co.co_name.startswith('_mm_repr_tuple'):
                    return
                raise OperationError(space.w_ReferenceError, w_tuple)
            w_tuple.delegating = delegation_forbidden
            return w_tuple
        if option.runappdirect:
            cls.w_forbid_delegation = lambda self, x: x
            cls.test_delegation = lambda self: skip("runappdirect")
        else:
            cls.w_forbid_delegation = cls.space.wrap(
                gateway.interp2app(forbid_delegation))

    def w_isspecialised(self, obj, expected=''):
        import __pypy__
        r = __pypy__.internal_repr(obj)
        print obj, '==>', r, '   (expected: %r)' % expected
        return ("SpecialisedTupleObject" + expected) in r

    def test_createspecialisedtuple(self):
        have = ['ii', 'ff', 'oo']
        #
        spec = {int: 'i',
                float: 'f',
                str: 's',
                list: 'o'}
        #
        for x in [42, 4.2, "foo", []]:
            for y in [43, 4.3, "bar", []]:
                expected1 = spec[type(x)]
                expected2 = spec[type(y)]
                if expected1 + expected2 not in have:
                    expected1 = expected2 = 'o'
                obj = (x, y)
                assert self.isspecialised(obj, '_' + expected1 + expected2)
        #
        if 'ooo' in have:
            obj = (1, 2, 3)
            assert self.isspecialised(obj, '_ooo')

    def test_delegation(self):
        t = self.forbid_delegation((42, 43))
        raises(ReferenceError, t.__getslice__, 0, 1)

    def test_len(self):
        t = self.forbid_delegation((42,43))
        assert len(t) == 2

    def test_notspecialisedtuple(self):
        assert not self.isspecialised((42,43,44,45))
        assert not self.isspecialised((1.5,))

    def test_slicing_to_specialised(self):
        t = (1, 2, 3)
        assert self.isspecialised(t[0:2])
        t = (1, '2', 3)
        assert self.isspecialised(t[0:5:2])

    def test_adding_to_specialised(self):
        t = (1,)
        assert self.isspecialised(t + (2,))

    def test_multiply_to_specialised(self):
        t = (1,)
        assert self.isspecialised(t * 2)

    def test_slicing_from_specialised(self):
        t = (1, 2, 3)
        assert t[0:2:1] == (1, 2)

    def test_eq_no_delegation(self):
        t = (1,)
        a = self.forbid_delegation(t + (2,))
        b = (1, 2)
        assert a == b

        c = (2, 1)
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
        a = (1,2) #self.forbid_delegation((1,2)) --- code commented out
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

        assert (2,2) > a
        assert (1,3) > a
        assert not (1,2) > a
           
        assert (2,2) >= a
        assert (1,2) >= a
        assert not (1,1) >= a
           
        assert (0,2) <= a
        assert (1,2) <= a
        assert not (1,3) <= a
        
        assert (0,2) < a
        assert (1,1) < a
        assert not (1,3) < a

    def test_hash(self):
        a = (1,2)
        b = (1,)
        b += (2,) # else a and b refer to same constant
        assert hash(a) == hash(b)

        c = (2,4)
        assert hash(a) != hash(c)

        assert hash(a) == hash((1L, 2L)) == hash((1.0, 2.0)) == hash((1.0, 2L))

    def test_getitem(self):
        t = self.forbid_delegation((5,3))
        assert (t)[0] == 5
        assert (t)[1] == 3
        assert (t)[-1] == 3
        assert (t)[-2] == 5
        raises(IndexError, "t[2]")
        raises(IndexError, "t[-3]")

    def test_three_tuples(self):
        if not self.isspecialised((1, 2, 3)):
            skip("don't have specialization for 3-tuples")
        b = self.forbid_delegation((1, 2, 3))
        c = (1,)
        d = c + (2, 3)
        assert self.isspecialised(d)
        assert b == d

    def test_mongrel(self):
        a = self.forbid_delegation((2.2, '333'))
        assert self.isspecialised(a)
        assert len(a) == 2
        assert a[0] == 2.2 and a[1] == '333'
        b = ('333',)
        assert a == (2.2,) + b
        assert not a != (2.2,) + b
        #
        if not self.isspecialised((1, 2, 3)):
            skip("don't have specialization for 3-tuples")
        a = self.forbid_delegation((1, 2.2, '333'))
        assert self.isspecialised(a)
        assert len(a) == 3
        assert a[0] == 1 and a[1] == 2.2 and a[2] == '333'
        b = ('333',)
        assert a == (1, 2.2,) + b
        assert not a != (1, 2.2) + b


class AppTestAll(test_tupleobject.AppTestW_TupleObject):
    pass
