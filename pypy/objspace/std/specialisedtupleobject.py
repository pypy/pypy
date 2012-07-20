from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.tupleobject import W_AbstractTupleObject
from pypy.objspace.std.tupleobject import W_TupleObject
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import compute_hash
from pypy.rlib.unroll import unrolling_iterable
from pypy.tool.sourcetools import func_with_new_name

class NotSpecialised(Exception):
    pass

class W_SpecialisedTupleObject(W_AbstractTupleObject):
    from pypy.objspace.std.tupletype import tuple_typedef as typedef
    __slots__ = []

    def __repr__(self):
        """ representation for debugging purposes """
        reprlist = [repr(item) for item in self._to_unwrapped_list()]
        return "%s(%s)" % (self.__class__.__name__, ', '.join(reprlist))

    #def tolist(self):   --- inherited from W_AbstractTupleObject
    #    raise NotImplementedError

    def _to_unwrapped_list(self):
        "NOT_RPYTHON"
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

    def delegating(self):
        pass     # for tests only


def make_specialised_class(typetuple):
    assert type(typetuple) == tuple
    
    nValues = len(typetuple)
    iter_n = unrolling_iterable(range(nValues))
    
    class cls(W_SpecialisedTupleObject):
        def __init__(self, space, *values_w):
            self.space = space
            assert len(values_w) == nValues
            for i in iter_n:
                w_obj = values_w[i]
                val_type = typetuple[i]
                if val_type == int:
                    unwrapped = space.int_w(w_obj)
                elif val_type == float:
                    unwrapped = space.float_w(w_obj)
                elif val_type == str:
                    unwrapped = space.str_w(w_obj)
                elif val_type == object:
                    unwrapped = w_obj
                else:
                    raise AssertionError
                setattr(self, 'value%s' % i, unwrapped)

        def length(self):
            return nValues

        def tolist(self):
            list_w = [None] * nValues            
            for i in iter_n:
                value = getattr(self, 'value%s' % i)
                if typetuple[i] != object:
                    value = self.space.wrap(value)
                list_w[i] = value
            return list_w

        # same source code, but builds and returns a resizable list
        getitems_copy = func_with_new_name(tolist, 'getitems_copy')

        def _to_unwrapped_list(self):
            "NOT_RPYTHON"
            list_w = [None] * nValues
            for i in iter_n:
                value = getattr(self, 'value%s' % i)
                if typetuple[i] == object:
                    value = self.space.unwrap(value)
                list_w[i] = value
            return list_w

        def hash(self, space):
            # XXX duplicate logic from tupleobject.py
            mult = 1000003
            x = 0x345678
            z = nValues
            for i in iter_n:
                value = getattr(self, 'value%s' % i)
                if typetuple[i] == object:
                    y = space.int_w(space.hash(value))
                elif typetuple[i] == float:
                    # get the correct hash for float which is an
                    # integer & other less frequent cases
                    from pypy.objspace.std.floatobject import _hash_float
                    y = _hash_float(space, value)
                else:
                    y = compute_hash(value)
                x = (x ^ y) * mult
                z -= 1
                mult += 82520 + z + z
            x += 97531
            return space.wrap(intmask(x))

        def _eq(self, w_other):
            if not isinstance(w_other, cls):
                # if we are not comparing same types, give up
                raise FailedToImplement
            for i in iter_n:
                myval    = getattr(self,    'value%s' % i)
                otherval = getattr(w_other, 'value%s' % i)
                if typetuple[i] == object:
                    if not self.space.eq_w(myval, otherval):
                        return False
                else:
                    if myval != otherval:
                        return False
            else:
                return True

        def eq(self, space, w_other):
            return space.newbool(self._eq(w_other))

        def ne(self, space, w_other):
            return space.newbool(not self._eq(w_other))

##        def _compare(self, compare_op, w_other):
##            if not isinstance(w_other, cls):
##                raise FailedToImplement
##            ncmp = min(self.length(), w_other.length())
##            for i in iter_n:
##                if typetuple[i] == Any:#like space.eq on wrapped or two params?
##                    raise FailedToImplement
##                if ncmp > i:
##                    l_val = getattr(self, 'value%s' % i)
##                    r_val = getattr(w_other, 'value%s' % i)
##                    if l_val != r_val:
##                        return compare_op(l_val, r_val)
##            return compare_op(self.length(), w_other.length())

        def getitem(self, index):
            for i in iter_n:
                if index == i:
                    value = getattr(self, 'value%s' % i)
                    if typetuple[i] != object:
                        value = self.space.wrap(value)
                    return value
            raise IndexError

    cls.__name__ = ('W_SpecialisedTupleObject_' +
                    ''.join([t.__name__[0] for t in typetuple]))
    _specialisations.append(cls)
    return cls

# ---------- current specialized versions ----------

_specialisations = []
Cls_ii = make_specialised_class((int, int))
#Cls_is = make_specialised_class((int, str))
#Cls_io = make_specialised_class((int, object))
#Cls_si = make_specialised_class((str, int))
#Cls_ss = make_specialised_class((str, str))
#Cls_so = make_specialised_class((str, object))
#Cls_oi = make_specialised_class((object, int))
#Cls_os = make_specialised_class((object, str))
Cls_oo = make_specialised_class((object, object))
Cls_ff = make_specialised_class((float, float))
#Cls_ooo = make_specialised_class((object, object, object))

def makespecialisedtuple(space, list_w):
    if len(list_w) == 2:
        w_arg1, w_arg2 = list_w
        w_type1 = space.type(w_arg1)
        #w_type2 = space.type(w_arg2)
        #
        if w_type1 is space.w_int:
            w_type2 = space.type(w_arg2)
            if w_type2 is space.w_int:
                return Cls_ii(space, w_arg1, w_arg2)
            #elif w_type2 is space.w_str:
            #    return Cls_is(space, w_arg1, w_arg2)
            #else:
            #    return Cls_io(space, w_arg1, w_arg2)
        #
        #elif w_type1 is space.w_str:
        #    if w_type2 is space.w_int:
        #        return Cls_si(space, w_arg1, w_arg2)
        #    elif w_type2 is space.w_str:
        #        return Cls_ss(space, w_arg1, w_arg2)
        #    else:
        #        return Cls_so(space, w_arg1, w_arg2)
        #
        elif w_type1 is space.w_float:
            w_type2 = space.type(w_arg2)
            if w_type2 is space.w_float:
                return Cls_ff(space, w_arg1, w_arg2)
        #
        #else:
        #    if w_type2 is space.w_int:
        #        return Cls_oi(space, w_arg1, w_arg2)
        #    elif w_type2 is space.w_str:
        #        return Cls_os(space, w_arg1, w_arg2)
        #    else:
        return Cls_oo(space, w_arg1, w_arg2)
        #
    #elif len(list_w) == 3:
    #    return Cls_ooo(space, list_w[0], list_w[1], list_w[2])
    else:
        raise NotSpecialised

# ____________________________________________________________

registerimplementation(W_SpecialisedTupleObject)

def delegate_SpecialisedTuple2Tuple(space, w_specialised):
    w_specialised.delegating()
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

##from operator import lt, le, ge, gt   
 
##def lt__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
##    return space.newbool(w_tuple1._compare(lt, w_tuple2))

##def le__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
##    return space.newbool(w_tuple1._compare(le, w_tuple2))

##def ge__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
##    return space.newbool(w_tuple1._compare(ge, w_tuple2))

##def gt__SpecialisedTuple_SpecialisedTuple(space, w_tuple1, w_tuple2):
##    return space.newbool(w_tuple1._compare(gt, w_tuple2))

def hash__SpecialisedTuple(space, w_tuple):
    return w_tuple.hash(space)

from pypy.objspace.std import tupletype
register_all(vars(), tupletype)
