"""Generic iterator implementations"""
from pypy.interpreter.error import OperationError
from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all


def length_hint(space, w_obj, default):
    """Return the length of an object, consulting its __length_hint__
    method if necessary.
    """
    try:
        return space.len_w(w_obj)
    except OperationError, e:
        if not (e.match(space, space.w_TypeError) or
                e.match(space, space.w_AttributeError)):
            raise

    try:
        w_hint = space.call_method(w_obj, '__length_hint__')
    except OperationError, e:
        if not (e.match(space, space.w_TypeError) or
                e.match(space, space.w_AttributeError)):
            raise
        return default

    hint = space.int_w(w_hint)
    return default if hint < 0 else hint


class W_AbstractIterObject(W_Object):
    __slots__ = ()

class W_AbstractSeqIterObject(W_AbstractIterObject):
    from pypy.objspace.std.itertype import iter_typedef as typedef

    def __init__(w_self, w_seq, index=0):
        if index < 0:
            index = 0
        w_self.w_seq = w_seq
        w_self.index = index

    def getlength(self, space):
        if self.w_seq is None:
            return space.wrap(0)
        index = self.index
        w_length = space.len(self.w_seq)
        w_len = space.sub(w_length, space.wrap(index))
        if space.is_true(space.lt(w_len, space.wrap(0))):
            w_len = space.wrap(0)
        return w_len

class W_SeqIterObject(W_AbstractSeqIterObject):
    """Sequence iterator implementation for general sequences."""

class W_FastListIterObject(W_AbstractSeqIterObject): # XXX still needed
    """Sequence iterator specialized for lists.
    """

class W_FastTupleIterObject(W_AbstractSeqIterObject):
    """Sequence iterator specialized for tuples, accessing directly
    their RPython-level list of wrapped objects.
    """
    def __init__(w_self, w_seq, wrappeditems):
        W_AbstractSeqIterObject.__init__(w_self, w_seq)
        w_self.tupleitems = wrappeditems

class W_ReverseSeqIterObject(W_Object):
    from pypy.objspace.std.itertype import reverse_iter_typedef as typedef

    def __init__(w_self, space, w_seq, index=-1):
        w_self.w_seq = w_seq
        w_self.w_len = space.len(w_seq)
        w_self.index = space.int_w(w_self.w_len) + index


registerimplementation(W_SeqIterObject)
registerimplementation(W_FastListIterObject)
registerimplementation(W_FastTupleIterObject)
registerimplementation(W_ReverseSeqIterObject)

def iter__SeqIter(space, w_seqiter):
    return w_seqiter

def next__SeqIter(space, w_seqiter):
    if w_seqiter.w_seq is None:
        raise OperationError(space.w_StopIteration, space.w_None)
    try:
        w_item = space.getitem(w_seqiter.w_seq, space.wrap(w_seqiter.index))
    except OperationError, e:
        w_seqiter.w_seq = None
        if not e.match(space, space.w_IndexError):
            raise
        raise OperationError(space.w_StopIteration, space.w_None)
    w_seqiter.index += 1
    return w_item


def iter__FastTupleIter(space, w_seqiter):
    return w_seqiter

def next__FastTupleIter(space, w_seqiter):
    if w_seqiter.tupleitems is None:
        raise OperationError(space.w_StopIteration, space.w_None)
    index = w_seqiter.index
    try:
        w_item = w_seqiter.tupleitems[index]
    except IndexError:
        w_seqiter.tupleitems = None
        w_seqiter.w_seq = None
        raise OperationError(space.w_StopIteration, space.w_None)
    w_seqiter.index = index + 1
    return w_item


def iter__FastListIter(space, w_seqiter):
    return w_seqiter

def next__FastListIter(space, w_seqiter):
    from pypy.objspace.std.listobject import W_ListObject
    w_seq = w_seqiter.w_seq
    if w_seq is None:
        raise OperationError(space.w_StopIteration, space.w_None)
    assert isinstance(w_seq, W_ListObject)
    index = w_seqiter.index
    try:
        w_item = w_seq.getitem(index)
    except IndexError:
        w_seqiter.w_seq = None
        raise OperationError(space.w_StopIteration, space.w_None)
    w_seqiter.index = index + 1
    return w_item


def iter__ReverseSeqIter(space, w_seqiter):
    return w_seqiter

def next__ReverseSeqIter(space, w_seqiter):
    if w_seqiter.w_seq is None or w_seqiter.index < 0:
        raise OperationError(space.w_StopIteration, space.w_None)
    try:
        w_item = space.getitem(w_seqiter.w_seq, space.wrap(w_seqiter.index))
        w_seqiter.index -= 1
    except OperationError, e:
        w_seqiter.w_seq = None
        if not e.match(space, space.w_IndexError):
            raise
        raise OperationError(space.w_StopIteration, space.w_None)
    return w_item

register_all(vars())
