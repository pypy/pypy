from objspace import *


class W_SeqIterObject:
    delegate_once = {}

    def __init__(self, w_seq, index=0):
        self.w_seq = w_seq
        self.index = index


def iter_seqiter(space, w_seqiter):
    return w_seqiter

StdObjSpace.iter.register(iter_seqiter, W_SeqIterObject)

def next_seqiter(space, w_seqiter):
    try:
        w_item = space.getitem(w_seqiter.w_seq, space.wrap(w_seqiter.index))
    except OperationError, e:
        if e.match(space, space.w_IndexError):
            raise NoValue
        raise
    w_seqiter.index += 1
    return w_item

StdObjSpace.next.register(next_seqiter, W_SeqIterObject)
