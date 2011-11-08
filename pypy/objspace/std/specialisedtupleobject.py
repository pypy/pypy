from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import compute_hash
from pypy.rlib.unroll import unrolling_iterable

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
                        

def make_specialised_class(typetuple):
    assert type(typetuple) == tuple
    iter_n = unrolling_iterable(range(len(typetuple)))
    class cls(W_SpecialisedTupleObject):
        def __init__(self, space, *values):
            assert len(typetuple) == len(values)
            for i in iter_n:
                assert isinstance(values[i], typetuple[i])
            self.space = space
            for i in iter_n:
                setattr(self, 'value%s' % i, values[i])
    
        def length(self):
            return len(typetuple)
    
        def tolist(self):
            return [self.space.wrap(getattr(self, 'value%s' % i)) for i in iter_n]
            
        def hash(self, space):
            mult = 1000003
            x = 0x345678
            z = 2
            for i in iter_n:
#                y = compute_hash(val)
                y = space.int_w(space.hash(space.wrap(getattr(self, 'value%s' % i))))                		
                x = (x ^ y) * mult
                z -= 1
                mult += 82520 + z + z
            x += 97531
            return space.wrap(intmask(x))
    
        def _eq(self, w_other):
            if not isinstance(w_other, cls): #so we will be sure we are comparing same types
                raise FailedToImplement
            for i in iter_n:
                if getattr(self, 'value%s' % i) != getattr(w_other, 'value%s' % i):
                    return False
            else:
                return True
    
        def eq(self, space, w_other):
            return space.newbool(self._eq(w_other))
    
        def ne(self, space, w_other):
            return space.newbool(not self._eq(w_other))
    
        def _compare(self, compare_op, w_other):
            if not isinstance(w_other, cls):
                raise FailedToImplement
            ncmp = min(self.length(), w_other.length())
            for i in iter_n:
                if ncmp > i:
                    l_val = getattr(self, 'value%s' % i)
                    r_val = getattr(w_other, 'value%s' % i)
                    if l_val != r_val:
                        return compare_op(l_val, r_val)
            return compare_op(self.length(), w_other.length())
            
        def getitem(self, index):
            for i in iter_n:
                if index == i:
                    return self.space.wrap(getattr(self, 'value%s' % i))
            raise IndexError

    cls.__name__ = 'W_SpecialisedTupleObject' + ''.join([t.__name__.capitalize() for t in typetuple])      
    _specialisations.append((cls,typetuple))
    return cls
    
    
W_SpecialisedTupleObjectIntInt     = make_specialised_class((int,int))
W_SpecialisedTupleObjectIntIntInt  = make_specialised_class((int,int,int))
W_SpecialisedTupleObjectFloatFloat = make_specialised_class((float,float))
W_SpecialisedTupleObjectStrStr     = make_specialised_class((str, str))
W_SpecialisedTupleObjectIntFloatStr= make_specialised_class((int, float, str))

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

def getitem__SpecialisedTuple_Slice(space, w_tuple, w_slice):
    length = w_tuple.length()
    start, stop, step, slicelength = w_slice.indices4(space, length)
    assert slicelength >= 0
    subitems = [None] * slicelength
    for i in range(slicelength):
        subitems[i] = w_tuple.getitem(start)
        start += step
    return space.newtuple(subitems)

def mul_specialisedtuple_times(space, w_tuple, w_times):
    try:
        times = space.getindex_w(w_times, space.w_OverflowError)
    except OperationError, e:
        if e.match(space, space.w_TypeError):
            raise FailedToImplement
        raise
    if times == 1 and space.type(w_tuple) == space.w_tuple:
        return w_tuple
    items = w_tuple.tolist()
    return space.newtuple(items * times)

def mul__SpecialisedTuple_ANY(space, w_tuple, w_times):
    return mul_specialisedtuple_times(space, w_tuple, w_times)

def mul__ANY_SpecialisedTuple(space, w_times, w_tuple):
    return mul_specialisedtuple_times(space, w_tuple, w_times)

def eq__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.eq(space, w_tuple2)

def ne__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.ne(space, w_tuple2)

from operator import lt, le, ge, gt   
 
def lt__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return space.newbool(w_tuple1._compare(lt, w_tuple2))

def le__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return space.newbool(w_tuple1._compare(le, w_tuple2))

def ge__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return space.newbool(w_tuple1._compare(ge, w_tuple2))

def gt__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return space.newbool(w_tuple1._compare(gt, w_tuple2))

def hash__SpecialisedTuple(space, w_tuple):
    return w_tuple.hash(space)

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)
