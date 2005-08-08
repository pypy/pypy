"""
Reviewed 03-06-22
Sequence-iteration is correctly implemented, thoroughly
tested, and complete. The only missing feature is support
for function-iteration.
"""
from pypy.objspace.std.objspace import *


class W_SeqIterObject(W_Object):
    from pypy.objspace.std.itertype import iter_typedef as typedef
    
    def __init__(w_self, space, w_seq, index=0, reverse=False):
        W_Object.__init__(w_self, space)
        w_self.w_seq = w_seq
        try:
            w_self.length = space.unwrap(space.len(w_seq))
        except OperationError,e:
            if e.match(space, space.w_TypeError):
                w_self.length = 0
            else:
                raise
        w_self.index = index
        if index < 0:
            w_self.index += w_self.length
        w_self.reverse = reverse
        w_self.consumed = 0

registerimplementation(W_SeqIterObject)


def iter__SeqIter(space, w_seqiter):
    return w_seqiter

def next__SeqIter(space, w_seqiter):
    if w_seqiter.w_seq is None:
        raise OperationError(space.w_StopIteration, space.w_None)
    try:
        if w_seqiter.index >=0:
            w_item = space.getitem(w_seqiter.w_seq, space.wrap(w_seqiter.index))
        else:
            raise OperationError(space.w_StopIteration, space.w_None) 
    except OperationError, e:
        w_seqiter.w_seq = None
        if not e.match(space, space.w_IndexError):
            raise
        raise OperationError(space.w_StopIteration, space.w_None) 
    if w_seqiter.reverse:
        w_seqiter.index -= 1
    else:
        w_seqiter.index += 1
    w_seqiter.consumed += 1
    return w_item

def len__SeqIter(space,  w_seqiter):
    if w_seqiter.w_seq is None :
        return space.wrap(0)
    w_index = space.sub(space.len(w_seqiter.w_seq), space.wrap(w_seqiter.index))
    if space.is_true(space.gt(space.len(w_seqiter.w_seq), space.wrap(w_seqiter.index))):
        if w_seqiter.reverse:
            w_len = space.wrap(w_seqiter.index+1)
        else: 
            w_len = space.sub(space.len(w_seqiter.w_seq), space.wrap(w_seqiter.consumed))
    else:
        w_seqiter.w_seq = None
        w_len = space.wrap(0)
    return w_len

register_all(vars())
