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
                        
class W_SpecialisedTupleObject1(W_SpecialisedTupleObject):	#one element tuples
    def __init__(self, value0):
        raise NotImplementedError

    def length(self):
        return 1

    def eq(self, space, w_other):
        if w_other.length() != 1:
            return space.w_False
        if self.value0 == w_other.value0:	#is it safe to assume all 1-tuples are specialised ?
            return space.w_True
        else:
            return space.w_False

    def hash(self, space):
        mult = 1000003
        x = 0x345678
        z = 1
        w_item = self.getitem(0)
        y = space.int_w(space.hash(w_item))
        x = (x ^ y) * mult
        mult += 82520 + z + z
        x += 97531
        return space.wrap(intmask(x))

class W_SpecialisedTupleObjectInt(W_SpecialisedTupleObject1):	#one integer element
    def __init__(self, intval):
        assert type(intval) == IntType#isinstance
        self.intval = intval#intval

    def tolist(self):
        return [W_IntObject(self.intval)]

    def getitem(self, index):
        if index == 0:
            return W_IntObject(self.intval)
        raise IndexError

    def setitem(self, index, w_item):
        assert isinstance(w_item, W_IntObject)
        if index == 0:
            self.intval = w_item.intval
            return
        raise IndexError
        
class W_SpecialisedTupleObjectFloat(W_SpecialisedTupleObject1):	#one integer element
    def __init__(self, floatval):
        assert type(floatval) == FloatType
        self.floatval = floatval

    def tolist(self):
        return [W_FloatObject(self.floatval)]

    def getitem(self, index):
        if index == 0:
            return W_FloatObject(self.floatval)
        raise IndexError

    def setitem(self, index, w_item):
        assert isinstance(w_item, W_FloatObject)
        if index == 0:
            self.floatval = w_item.floatval
            return
        raise IndexError
        
class W_SpecialisedTupleObjectString(W_SpecialisedTupleObject1):	#one integer element
    def __init__(self, stringval):
        assert type(stringval) == StringType
        self.stringval = stringval

    def tolist(self):
        return [W_StringObject(self.stringval)]

    def getitem(self, index):
        if index == 0:
            return W_StringObject(self.stringval)
        raise IndexError

    def setitem(self, index, w_item):
        assert isinstance(w_item, W_StringObject)
        if index == 0:
            self.stringval = w_item._value # does  _value need to be private
            return
        raise IndexError
        
'''        
        W_SpecialisedTupleObjectIntInt,	#two element tupes of int, float or string
        W_SpecialisedTupleObjectIntFloat,
        W_SpecialisedTupleObjectIntString,
        W_SpecialisedTupleObjectFloatInt,
        W_SpecialisedTupleObjectFloatFloat,
        W_SpecialisedTupleObjectFloatString,
        W_SpecialisedTupleObjectStringInt,
        W_SpecialisedTupleObjectStringFloat,
        W_SpecialisedTupleObjectStringString
        
'''
registerimplementation(W_SpecialisedTupleObject)

#---------
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

# getitem__SpecialisedTuple_Slice removed
# mul_specialisedtuple_times removed
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


# mul__SpecialisedTuple_ANY removed
# mul__ANY_SpecialisedTuple removed

def eq__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
    return w_tuple1.eq(space, w_tuple2)

def hash__SpecialisedTuple(space, w_tuple):
    return w_tuple.hash(space)

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)
