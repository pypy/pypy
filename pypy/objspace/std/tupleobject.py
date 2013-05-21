import sys
from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.inttype import wrapint
from rpython.rlib.rarithmetic import intmask
from pypy.objspace.std.sliceobject import W_SliceObject, normalize_simple_slice
from pypy.objspace.std import slicetype
from pypy.objspace.std.util import negate
from pypy.objspace.std.stdtypedef import StdTypeDef
from rpython.rlib.debug import make_sure_not_resized
from rpython.rlib import jit
from rpython.tool.sourcetools import func_with_new_name
from pypy.interpreter import gateway

UNROLL_CUTOFF = 10

class W_AbstractTupleObject(W_Object):
    __slots__ = ()

    def tolist(self):
        "Returns the items, as a fixed-size list."
        raise NotImplementedError

    def getitems_copy(self):
        "Returns a copy of the items, as a resizable list."
        raise NotImplementedError


def tuple_unroll_condition(space, self, w_other):
    return jit.loop_unrolling_heuristic(self, len(self.wrappeditems), UNROLL_CUTOFF) or \
           jit.loop_unrolling_heuristic(w_other, len(w_other.wrappeditems), UNROLL_CUTOFF)


class W_TupleObject(W_AbstractTupleObject):
    _immutable_fields_ = ['wrappeditems[*]']

    def __init__(w_self, wrappeditems):
        make_sure_not_resized(wrappeditems)
        w_self.wrappeditems = wrappeditems   # a list of wrapped values

    def __repr__(w_self):
        """ representation for debugging purposes """
        reprlist = [repr(w_item) for w_item in w_self.wrappeditems]
        return "%s(%s)" % (w_self.__class__.__name__, ', '.join(reprlist))

    def unwrap(w_tuple, space):
        items = [space.unwrap(w_item) for w_item in w_tuple.wrappeditems]
        return tuple(items)

    def tolist(self):
        return self.wrappeditems

    def getitems_copy(self):
        return self.wrappeditems[:]   # returns a resizable list

    @staticmethod
    def descr_new(space, w_tupletype, w_sequence=None):
        from pypy.objspace.std.tupleobject import W_TupleObject
        if w_sequence is None:
            tuple_w = []
        elif (space.is_w(w_tupletype, space.w_tuple) and
              space.is_w(space.type(w_sequence), space.w_tuple)):
            return w_sequence
        else:
            tuple_w = space.fixedview(w_sequence)
        w_obj = space.allocate_instance(W_TupleObject, w_tupletype)
        W_TupleObject.__init__(w_obj, tuple_w)
        return w_obj

    def descr_repr(self, space):
        items = self.wrappeditems
        # XXX this is quite innefficient, still better than calling
        #     it via applevel
        if len(items) == 1:
            return space.wrap("(" + space.str_w(space.repr(items[0])) + ",)")
        return space.wrap("(" +
                     (", ".join([space.str_w(space.repr(item)) for item in items]))
                          + ")")

    def descr_hash(self, space):
        return space.wrap(hash_tuple(space, self.wrappeditems))

    @jit.look_inside_iff(tuple_unroll_condition)
    def descr_eq(self, space, w_other):
        if not isinstance(w_other, W_TupleObject):
            return space.w_NotImplemented
        items1 = self.wrappeditems
        items2 = w_other.wrappeditems
        lgt1 = len(items1)
        lgt2 = len(items2)
        if lgt1 != lgt2:
            return space.w_False
        for i in range(lgt1):
            item1 = items1[i]
            item2 = items2[i]
            if not space.eq_w(item1, item2):
                return space.w_False
        return space.w_True

    descr_ne = negate(descr_eq)

    def _make_tuple_comparison(name):
        import operator
        op = getattr(operator, name)

        @jit.look_inside_iff(tuple_unroll_condition)
        def compare_tuples(self, space, w_other):
            if not isinstance(w_other, W_TupleObject):
                return space.w_NotImplemented
            items1 = self.wrappeditems
            items2 = w_other.wrappeditems
            ncmp = min(len(items1), len(items2))
            # Search for the first index where items are different
            for p in range(ncmp):
                if not space.eq_w(items1[p], items2[p]):
                    return getattr(space, name)(items1[p], items2[p])
            # No more items to compare -- compare sizes
            return space.newbool(op(len(items1), len(items2)))
        return func_with_new_name(compare_tuples, name + '__Tuple_Tuple')

    descr_lt = _make_tuple_comparison('lt')
    descr_le = _make_tuple_comparison('le')
    descr_gt = _make_tuple_comparison('gt')
    descr_ge = _make_tuple_comparison('ge')

    def descr_len(self, space):
        result = len(self.wrappeditems)
        return wrapint(space, result)

    def descr_iter(self, space):
        from pypy.objspace.std import iterobject
        return iterobject.W_FastTupleIterObject(self, self.wrappeditems)

    @jit.look_inside_iff(lambda self, space, w_obj:
            jit.loop_unrolling_heuristic(self, len(self.wrappeditems), UNROLL_CUTOFF))
    def descr_contains(self, space, w_obj):
        for w_item in self.wrappeditems:
            if space.eq_w(w_item, w_obj):
                return space.w_True
        return space.w_False

    def descr_add(self, space, w_other):
        if not isinstance(w_other, W_TupleObject):
            return space.w_NotImplemented
        items1 = self.wrappeditems
        items2 = w_other.wrappeditems
        return space.newtuple(items1 + items2)

    def descr_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        if times == 1 and space.type(self) == space.w_tuple:
            return self
        items = self.wrappeditems
        return space.newtuple(items * times)

    def descr_getitem(self, space, w_index):
        if isinstance(w_index, W_SliceObject):
            items = self.wrappeditems
            length = len(items)
            start, stop, step, slicelength = w_index.indices4(space, length)
            assert slicelength >= 0
            subitems = [None] * slicelength
            for i in range(slicelength):
                subitems[i] = items[start]
                start += step
            return space.newtuple(subitems)

        index = space.getindex_w(w_index, space.w_IndexError, "tuple index")
        try:
            return self.wrappeditems[index]
        except IndexError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("tuple index out of range"))

    def descr_getslice(self, space, w_start, w_stop):
        length = len(self.wrappeditems)
        start, stop = normalize_simple_slice(space, length, w_start, w_stop)
        return space.newtuple(self.wrappeditems[start:stop])

    def descr_getnewargs(self, space):
        return space.newtuple([space.newtuple(self.wrappeditems)])

    def descr_count(self, space, w_obj):
        """count(obj) -> number of times obj appears in the tuple"""
        count = 0
        for w_item in self.wrappeditems:
            if space.eq_w(w_item, w_obj):
                count += 1
        return space.wrap(count)

    @gateway.unwrap_spec(w_start=gateway.WrappedDefault(0),
                         w_stop=gateway.WrappedDefault(sys.maxint))
    def descr_index(self, space, w_obj, w_start, w_stop):
        """index(obj, [start, [stop]]) -> first index that obj appears in the
        tuple
        """
        length = len(self.wrappeditems)
        start, stop = slicetype.unwrap_start_stop(space, length, w_start, w_stop)
        for i in range(start, min(stop, length)):
            w_item = self.wrappeditems[i]
            if space.eq_w(w_item, w_obj):
                return space.wrap(i)
        raise OperationError(space.w_ValueError,
                             space.wrap("tuple.index(x): x not in tuple"))

W_TupleObject.typedef = StdTypeDef("tuple",
    __doc__ = '''tuple() -> an empty tuple
tuple(sequence) -> tuple initialized from sequence's items

If the argument is a tuple, the return value is the same object.''',
    __new__ = gateway.interp2app(W_TupleObject.descr_new),
    __repr__ = gateway.interp2app(W_TupleObject.descr_repr),
    __hash__ = gateway.interp2app(W_TupleObject.descr_hash),

    __eq__ = gateway.interp2app(W_TupleObject.descr_eq),
    __ne__ = gateway.interp2app(W_TupleObject.descr_ne),
    __lt__ = gateway.interp2app(W_TupleObject.descr_lt),
    __le__ = gateway.interp2app(W_TupleObject.descr_le),
    __gt__ = gateway.interp2app(W_TupleObject.descr_gt),
    __ge__ = gateway.interp2app(W_TupleObject.descr_ge),

    __len__ = gateway.interp2app(W_TupleObject.descr_len),
    __iter__ = gateway.interp2app(W_TupleObject.descr_iter),
    __contains__ = gateway.interp2app(W_TupleObject.descr_contains),

    __add__ = gateway.interp2app(W_TupleObject.descr_add),
    __mul__ = gateway.interp2app(W_TupleObject.descr_mul),
    __rmul__ = gateway.interp2app(W_TupleObject.descr_mul),

    __getitem__ = gateway.interp2app(W_TupleObject.descr_getitem),
    __getslice__ = gateway.interp2app(W_TupleObject.descr_getslice),

    __getnewargs__ = gateway.interp2app(W_TupleObject.descr_getnewargs),
    count = gateway.interp2app(W_TupleObject.descr_count),
    index = gateway.interp2app(W_TupleObject.descr_index)
)

registerimplementation(W_TupleObject)


@jit.look_inside_iff(lambda space, wrappeditems:
        jit.loop_unrolling_heuristic(wrappeditems, len(wrappeditems), UNROLL_CUTOFF))
def hash_tuple(space, wrappeditems):
    # this is the CPython 2.4 algorithm (changed from 2.3)
    mult = 1000003
    x = 0x345678
    z = len(wrappeditems)
    for w_item in wrappeditems:
        y = space.hash_w(w_item)
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return intmask(x)

from pypy.objspace.std import tupletype
tupletype.tuple_typedef = W_TupleObject.typedef
