from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std import slicetype
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import compute_hash

class NotSpecialised(Exception):
    pass         
            
_specialisations = []

def makespecialisedtuple(space, list_w):          
    w_type_of = {int:space.w_int, float:space.w_float, str:space.w_str}  
    unwrap_as = {int:space.int_w, float:space.float_w, str:space.str_w}  
    
    def try_specialisation((specialisedClass, paramtypes)):
        if len(list_w) != len(paramtypes):
            raise NotSpecialised
        for param,paramtype in zip(list_w,paramtypes):
            if space.type(param) != w_type_of[paramtype]:
                raise NotSpecialised
        unwrappedparams = [unwrap_as[paramtype](param) for param,paramtype in zip(list_w,paramtypes)]
        return specialisedClass(space, *unwrappedparams)
        
    for spec in _specialisations:
         try:
             return try_specialisation(spec)
         except NotSpecialised:
             pass
    raise NotSpecialised

class W_SpecialisedTupleObject(W_Object):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef
    __slots__ = []

    def tolist(self):
        raise NotImplementedError

    def _tolistunwrapped(self):
        raise NotImplementedError

    def length(self):
        raise NotImplementedError

    def getitem(self, index):
        raise NotImplementedError

    def hash(self, space):
        raise NotImplementedError

    def eq(self, space, w_other):
        raise NotImplementedError

    def setitem(self, index, w_item):
        raise NotImplementedError

    def unwrap(w_tuple, space):
        return tuple(self.tolist)
                        
def make_specialised_class(class_name, type0, type1):
    class cls(W_SpecialisedTupleObject):
        def __init__(self, space, val0, val1):
            assert isinstance(val0, type0)
            assert isinstance(val1, type1)
            self.space = space
            self.val0 = val0
            self.val1 = val1
    
        def length(self):
            return 2
    
        def tolist(self):
            return [self.space.wrap(self.val0), self.space.wrap(self.val1)]
            
        def hash(self, space):
            mult = 1000003
            x = 0x345678
            z = 2
            for val in [self.val0, self.val1]:
#                y = compute_hash(val)
                y = space.int_w(space.hash(space.wrap(val)))                		
                x = (x ^ y) * mult
                z -= 1
                mult += 82520 + z + z
            x += 97531
            return space.wrap(intmask(x))
    
        def eq(self, space, w_other):
            if w_other.length() != 2:
                return space.w_False
            if self.val0 == w_other.val0 and self.val1 == w_other.val1:	#xxx
                return space.w_True
            else:
                return space.w_False
    
        def ne(self, space, w_other):
            if w_other.length() != 2:
                return space.w_True
            if self.val0 != w_other.val0:
                return space.w_True
            if self.val1 != w_other.val1:
                return space.w_True
            return space.w_False
    
        def lt(self, space, w_other):
            assert self.length() <= 2
            ncmp = min(self.length(), w_other.length())
            if ncmp >= 1:
                if not self.val0 == w_other.val0:
                    return space.newbool(self.val0 < w_other.val0)
            if ncmp >= 2:
                if not self.val1 == w_other.val1:
                    return space.newbool(self.val1 < w_other.val1)
            return space.newbool(self.length() < w_other.length())
    
        def le(self, space, w_other):
            assert self.length() <= 2
            ncmp = min(self.length(), w_other.length())
            if ncmp >= 1:
                if not self.val0 == w_other.val0:
                    return space.newbool(self.val0 <= w_other.val0)
            if ncmp >= 2:
                if not self.val1 == w_other.val1:
                    return space.newbool(self.val1 <= w_other.val1)
            return space.newbool(self.length() <= w_other.length())
    
        def ge(self, space, w_other):
            assert self.length() <= 2
            ncmp = min(self.length(), w_other.length())
            if ncmp >= 1:
                if not self.val0 == w_other.val0:
                    return space.newbool(self.val0 >= w_other.val0)
            if ncmp >= 2:
                if not self.val1 == w_other.val1:
                    return space.newbool(self.val1 >= w_other.val1)
            return space.newbool(self.length() >= w_other.length())
    
        def gt(self, space, w_other):
            assert self.length() <= 2
            ncmp = min(self.length(), w_other.length())
            if ncmp >= 1:
                if not self.val0 == w_other.val0:
                    return space.newbool(self.val0 > w_other.val0)
            if ncmp >= 2:
                if not self.val1 == w_other.val1:
                    return space.newbool(self.val1 > w_other.val1)
            return space.newbool(self.length() > w_other.length())
    
        def getitem(self, index):
            if index == 0:
                return self.space.wrap(self.val0)
            if index == 1:
                return self.space.wrap(self.val1)
            raise IndexError
    cls.__name__ = class_name      
    _specialisations.append((cls,(type0,type1)))
    return cls
    
    
W_SpecialisedTupleObjectIntInt     = make_specialised_class('W_SpecialisedTupleObjectIntInt',     int,int)
W_SpecialisedTupleObjectFloatFloat = make_specialised_class('W_SpecialisedTupleObjectFloatFloat', float,float)
W_SpecialisedTupleObjectStrStr     = make_specialised_class('W_SpecialisedTupleObjectStrStr',     str, str)

registerimplementation(W_SpecialisedTupleObject)

def delegate_SpecialisedTuple2Tuple(space, w_specialised):
    return W_TupleObject(w_specialised.tolist())

def len__SpecialisedTuple(space, w_tuple):
    return space.wrap(w_tuple.length())

def getitem__SpecialisedTuple_ANY(space, w_tuple, w_index):
    index = space.getindex_w(w_index, space.w_IndexError, "tuple index")
    if index < 0:
        index += w_tuple.length()
    try:
        return w_tuple.getitem(index)
    except IndexError:
        raise OperationError(space.w_IndexError,
                             space.wrap("tuple index out of range"))

def eq__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.eq(space, w_tuple2)

def ne__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.ne(space, w_tuple2)

def lt__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.lt(space, w_tuple2)

def le__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.le(space, w_tuple2)

def ge__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.ge(space, w_tuple2)

def gt__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.gt(space, w_tuple2)

def hash__SpecialisedTuple(space, w_tuple):
    return w_tuple.hash(space)

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)
