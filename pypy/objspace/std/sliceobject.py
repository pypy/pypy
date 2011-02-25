"""Slice object"""

from pypy.interpreter.error import OperationError
from pypy.interpreter import gateway
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.slicetype import _Eval_SliceIndex

class W_SliceObject(W_Object):
    from pypy.objspace.std.slicetype import slice_typedef as typedef
    _immutable_fields_ = ['w_start', 'w_stop', 'w_step']

    def __init__(w_self, w_start, w_stop, w_step):
        assert w_start is not None
        assert w_stop is not None
        assert w_step is not None
        w_self.w_start = w_start
        w_self.w_stop = w_stop
        w_self.w_step = w_step

    def unwrap(w_slice, space):
        return slice(space.unwrap(w_slice.w_start), space.unwrap(w_slice.w_stop), space.unwrap(w_slice.w_step))

    def indices3(w_slice, space, length):
        if space.is_w(w_slice.w_step, space.w_None):
            step = 1
        else:
            step = _Eval_SliceIndex(space, w_slice.w_step)
            if step == 0:
                raise OperationError(space.w_ValueError,
                                     space.wrap("slice step cannot be zero"))
        if space.is_w(w_slice.w_start, space.w_None):
            if step < 0:
                start = length - 1
            else:
                start = 0
        else:
            start = _Eval_SliceIndex(space, w_slice.w_start)
            if start < 0:
                start += length
                if start < 0:
                    if step < 0:
                        start = -1
                    else:
                        start = 0
            elif start >= length:
                if step < 0:
                    start = length - 1
                else:
                    start = length
        if space.is_w(w_slice.w_stop, space.w_None):
            if step < 0:
                stop = -1
            else:
                stop = length
        else:
            stop = _Eval_SliceIndex(space, w_slice.w_stop)
            if stop < 0:
                stop += length
                if stop < 0:
                    if step < 0:
                        stop = -1
                    else:
                        stop = 0
            elif stop >= length:
                if step < 0:
                    stop = length - 1
                else:
                    stop = length
        return start, stop, step

    def indices4(w_slice, space, length):
        start, stop, step = w_slice.indices3(space, length)
        if (step < 0 and stop >= start) or (step > 0 and start >= stop):
            slicelength = 0
        elif step < 0:
            slicelength = (stop - start + 1) / step + 1
        else:
            slicelength = (stop - start - 1) / step + 1
        return start, stop, step, slicelength

    def __repr__(self):
        return "<W_SliceObject(%r, %r, %r)>" % (
            self.w_start, self.w_stop, self.w_step)

registerimplementation(W_SliceObject)


def normalize_simple_slice(space, length, w_start, w_stop):
    """Helper for the {get,set,del}slice multimethod implementations."""
    # this returns a pair (start, stop) which is usable for slicing
    # a sequence of the given length in the most friendly way, i.e.
    # guaranteeing that 0 <= start <= stop <= length.
    start = space.int_w(w_start)
    stop = space.int_w(w_stop)
    assert length >= 0
    if start < 0:
        start = 0
    if stop < start:
        stop = start
    if stop > length:
        stop = length
        if start > length:
            start = length
    return start, stop


repr__Slice = gateway.applevel("""
    def repr__Slice(aslice):
        return 'slice(%r, %r, %r)' % (aslice.start, aslice.stop, aslice.step)
""", filename=__file__).interphook("repr__Slice")

def eq__Slice_Slice(space, w_slice1, w_slice2):
    # We need this because CPython considers that slice1 == slice1
    # is *always* True (e.g. even if slice1 was built with non-comparable
    # parameters
    if space.is_w(w_slice1, w_slice2):
        return space.w_True
    if space.eq_w(w_slice1.w_start, w_slice2.w_start) and \
        space.eq_w(w_slice1.w_stop, w_slice2.w_stop) and \
        space.eq_w(w_slice1.w_step, w_slice2.w_step):
        return space.w_True
    else:
        return space.w_False

def lt__Slice_Slice(space, w_slice1, w_slice2):
    if space.is_w(w_slice1, w_slice2):
        return space.w_False   # see comments in eq__Slice_Slice()
    if space.eq_w(w_slice1.w_start, w_slice2.w_start):
        if space.eq_w(w_slice1.w_stop, w_slice2.w_stop):
            return space.lt(w_slice1.w_step, w_slice2.w_step)
        else:
            return space.lt(w_slice1.w_stop, w_slice2.w_stop)
    else:
        return space.lt(w_slice1.w_start, w_slice2.w_start)

# indices impl

def slice_indices__Slice_ANY(space, w_slice, w_length):
    length = space.getindex_w(w_length, space.w_OverflowError)
    start, stop, step = w_slice.indices3(space, length)
    return space.newtuple([space.wrap(start), space.wrap(stop),
                           space.wrap(step)])

# register all methods
from pypy.objspace.std import slicetype
register_all(vars(), slicetype)
