"""
Reviewed 03-06-22
Sequence-iteration is correctly implemented, thoroughly
tested, and complete. The only missing feature is support
for function-iteration.
"""
from pypy.objspace.std.objspace import *
from itertype import W_SeqIterType


class W_SeqIterObject(W_Object):
    statictype = W_SeqIterType

    def __init__(w_self, space, w_seq, index=0):
        W_Object.__init__(w_self, space)
        w_self.w_seq = w_seq
        w_self.index = index


registerimplementation(W_SeqIterObject)


def iter__SeqIter(space, w_seqiter):
    return w_seqiter

def next__SeqIter(space, w_seqiter):
    try:
        w_item = space.getitem(w_seqiter.w_seq, space.wrap(w_seqiter.index))
    except OperationError, e:
        if e.match(space, space.w_IndexError):
            raise NoValue
        raise
    w_seqiter.index += 1
    return w_item

register_all(vars())
