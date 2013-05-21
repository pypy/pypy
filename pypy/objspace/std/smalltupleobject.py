from pypy.interpreter.error import OperationError
from pypy.objspace.std.sliceobject import W_SliceObject
from pypy.objspace.std.tupleobject import W_AbstractTupleObject
from pypy.objspace.std.util import negate
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.unroll import unrolling_iterable
from rpython.tool.sourcetools import func_with_new_name


def make_specialized_class(n):
    iter_n = unrolling_iterable(range(n))
    class cls(W_AbstractTupleObject):

        def __init__(self, values):
            assert len(values) == n
            for i in iter_n:
                setattr(self, 'w_value%s' % i, values[i])

        def tolist(self):
            l = [None] * n
            for i in iter_n:
                l[i] = getattr(self, 'w_value%s' % i)
            return l

        # same source code, but builds and returns a resizable list
        getitems_copy = func_with_new_name(tolist, 'getitems_copy')

        def length(self):
            return n

        def descr_getitem(self, space, w_index):
            if isinstance(w_index, W_SliceObject):
                return self._getslice(space, w_index)
            index = space.getindex_w(w_index, space.w_IndexError,
                                     "tuple index")
            if index < 0:
                index += self.length()
            return self.getitem(space, index)

        def getitem(self, space, index):
            for i in iter_n:
                if index == i:
                    return getattr(self,'w_value%s' % i)
            raise OperationError(space.w_IndexError,
                                 space.wrap("tuple index out of range"))

        def descr_eq(self, space, w_other):
            if not isinstance(w_other, W_AbstractTupleObject):
                return space.w_NotImplemented
            if n != w_other.length():
                return space.w_False
            for i in iter_n:
                item1 = getattr(self,'w_value%s' % i)
                item2 = w_other.getitem(space, i)
                if not space.eq_w(item1, item2):
                    return space.w_False
            return space.w_True

        descr_ne = negate(descr_eq)

        def descr_hash(self, space):
            mult = 1000003
            x = 0x345678
            z = n
            for i in iter_n:
                w_item = getattr(self, 'w_value%s' % i)
                y = space.int_w(space.hash(w_item))
                x = (x ^ y) * mult
                z -= 1
                mult += 82520 + z + z
            x += 97531
            return space.wrap(intmask(x))

    cls.__name__ = "W_SmallTupleObject%s" % n
    return cls

W_SmallTupleObject2 = make_specialized_class(2)
W_SmallTupleObject3 = make_specialized_class(3)
W_SmallTupleObject4 = make_specialized_class(4)
W_SmallTupleObject5 = make_specialized_class(5)
W_SmallTupleObject6 = make_specialized_class(6)
W_SmallTupleObject7 = make_specialized_class(7)
W_SmallTupleObject8 = make_specialized_class(8)
