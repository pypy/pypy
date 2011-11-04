from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.inttype import wrapint
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.floatobject import W_FloatObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std import slicetype
from pypy.rlib.rarithmetic import intmask
from pypy.objspace.std.tupleobject import W_TupleObject

from  types import IntType, FloatType, StringType

class W_SpecialisedTupleObject(W_Object):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef

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
                        

class W_SpecialisedTupleObjectIntInt(W_SpecialisedTupleObject):
    def __init__(self, intval0, intval1):
        assert isinstance(intval0, int)
        assert isinstance(intval1, int)
        self.intval0 = intval0
        self.intval1 = intval1

    def length(self):
        return 2
'''
    def tolist(self):
        return [W_IntObject(self.intval)]

    def getitem(self, index):
        if index == 0:
            self.wrap(self.intval)
            return W_IntObject(self.intval)
        raise IndexError

    def setitem(self, index, w_item):
        assert isinstance(w_item, W_IntObject)
        if index == 0:
            self.intval = w_item.intval
            return
        raise IndexError
        
    def eq(self, space, w_other):
        if w_other.length() != 1:
            return space.w_False
        if self.intval == w_other.intval:	#is it safe to assume all 1-tuples are specialised ?
            return space.w_True
        else:
            return space.w_False
'''

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

def hash__SpecialisedTuple(space, w_tuple):
    return w_tuple.hash(space)

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)
