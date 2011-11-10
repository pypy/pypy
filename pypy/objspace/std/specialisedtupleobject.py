from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std.floatobject import _hash_float
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import compute_hash
from pypy.rlib.unroll import unrolling_iterable

class ANY(type):
    pass

class NotSpecialised(Exception):
    pass         

_specialisations = []

def makespecialisedtuple(space, list_w):          
    for specialisedClass in unrolling_iterable(_specialisations):
            try:
                return specialisedClass.try_specialisation(space, list_w)
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

    def unwrap(self, space):
        return tuple(self._to_unwrapped_list())
                        

def make_specialised_class(typetuple):
    assert type(typetuple) == tuple
    
    nValues = len(typetuple)
    iter_n = unrolling_iterable(range(nValues))
    
    class cls(W_SpecialisedTupleObject):
        def __init__(self, space, values):
            print cls,cls.__class__, values
            assert len(values) == nValues
            for i in iter_n:
                if typetuple[i] != ANY:
                    assert isinstance(values[i], typetuple[i])
            self.space = space
            for i in iter_n:
                setattr(self, 'value%s' % i, values[i])
                
        
        @classmethod
        def try_specialisation(cls, space, paramlist):
            if len(paramlist) != nValues:
                raise NotSpecialised
            for param,val_type in unrolling_iterable(zip(paramlist, typetuple)):
                if val_type == int:
                    if space.type(param) != space.w_int:
                        raise NotSpecialised
                elif val_type == float:
                    if space.type(param) != space.w_float:
                        raise NotSpecialised
                elif val_type == str:
                    if space.type(param) != space.w_str:
                        raise NotSpecialised
                elif val_type == ANY:
                    pass
                else:
                    raise NotSpecialised 
            unwrappedparams = [None] * nValues            
            for i in iter_n:
                if typetuple[i] == int:
                    unwrappedparams[i] = space.int_w(paramlist[i])
                elif typetuple[i] == float:
                    unwrappedparams[i] = space.float_w(paramlist[i])
                elif typetuple[i] == str:
                    unwrappedparams[i] = space.str_w(paramlist[i])
                elif typetuple[i] == ANY:
                    unwrappedparams[i] = paramlist[i]
                else:
                    raise NotSpecialised 
            return cls(space, unwrappedparams)
    
        def length(self):
            return nValues
    
        def tolist(self):
            list_w = [None] * nValues            
            for i in iter_n:
                if typetuple[i] == ANY:
                    list_w[i] = getattr(self, 'value%s' % i)
                else:
                    list_w[i] = self.space.wrap(getattr(self, 'value%s' % i))
            return list_w
            
        def _to_unwrapped_list(self):
            list_w = [None] * nValues            
            for i in iter_n:
                if typetuple[i] == ANY:
                    list_w[i] = space.unwrap(getattr(self, 'value%s' % i))#xxx
                else:
                    list_w[i] = getattr(self, 'value%s' % i)
            return list_w
                        
        def hash(self, space):
            mult = 1000003
            x = 0x345678
            z = 2
            for i in iter_n:
                value = getattr(self, 'value%s' % i)
                if typetuple[i] == ANY:
                    y = space.int_w(space.hash(value))    
                elif typetuple[i] == float: # get correct hash for float which is an integer & other less frequent cases
                    y = _hash_float(space, value)
                else:
                    y = compute_hash(value)
                x = (x ^ y) * mult
                z -= 1
                mult += 82520 + z + z
            x += 97531
            return space.wrap(intmask(x))
    
        def _eq(self, w_other):
            if not isinstance(w_other, cls): #so we will be sure we are comparing same types
                raise FailedToImplement
            for i in iter_n:
                if typetuple[i] == ANY:
                    if not self.space.is_true(self.space.eq(getattr(self, 'value%s' % i), getattr(w_other, 'value%s' % i))):
                       return False
                else:
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
                if typetuple[i] == ANY:#like space.eq on wrapped or two params?
                    raise FailedToImplement
                if ncmp > i:
                    l_val = getattr(self, 'value%s' % i)
                    r_val = getattr(w_other, 'value%s' % i)
                    if l_val != r_val:
                        return compare_op(l_val, r_val)
            return compare_op(self.length(), w_other.length())
            
        def getitem(self, index):
            for i in iter_n:
                if index == i:
                    if typetuple[i] == ANY:
                        return getattr(self, 'value%s' % i)
                    else:
                        return self.space.wrap(getattr(self, 'value%s' % i))
            raise IndexError

    cls.__name__ = 'W_SpecialisedTupleObject' + ''.join([t.__name__.capitalize() for t in typetuple])      
    _specialisations.append(cls)
    return cls
    
    
W_SpecialisedTupleObjectIntInt     = make_specialised_class((int,int))
W_SpecialisedTupleObjectIntAny     = make_specialised_class((int, ANY))
W_SpecialisedTupleObjectIntIntInt  = make_specialised_class((int,int,int))
W_SpecialisedTupleObjectFloatFloat = make_specialised_class((float,float))
W_SpecialisedTupleObjectStrStr     = make_specialised_class((str, str))
W_SpecialisedTupleObjectStrAny     = make_specialised_class((str, ANY))
W_SpecialisedTupleObjectIntFloatStr= make_specialised_class((int, float, str))
W_SpecialisedTupleObjectIntStrFloatAny= make_specialised_class((int, float, str, ANY))

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
