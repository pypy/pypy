from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp2app, make_weakref_descr
from pypy.interpreter.gateway import ObjSpace, W_Root, unwrap_spec, Arguments
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.error import OperationError
from pypy.rlib.debug import check_nonneg


# A `dequeobject` is composed of a doubly-linked list of `block` nodes.
# This list is not circular (the leftmost block has leftlink==NULL,
# and the rightmost block has rightlink==NULL).  A deque d's first
# element is at d.leftblock[leftindex] and its last element is at
# d.rightblock[rightindex]; note that, unlike as for Python slice
# indices, these indices are inclusive on both ends.  By being inclusive
# on both ends, algorithms for left and right operations become
# symmetrical which simplifies the design.
#
# The list of blocks is never empty, so d.leftblock and d.rightblock
# are never equal to NULL.
#
# The indices, d.leftindex and d.rightindex are always in the range
#     0 <= index < BLOCKLEN.
# Their exact relationship is:
#     (d.leftindex + d.len - 1) % BLOCKLEN == d.rightindex.
#
# Empty deques have d.len == 0; d.leftblock==d.rightblock;
# d.leftindex == CENTER+1; and d.rightindex == CENTER.
# Checking for d.len == 0 is the intended way to see whether d is empty.
#
# Whenever d.leftblock == d.rightblock,
#     d.leftindex + d.len - 1 == d.rightindex.
#
# However, when d.leftblock != d.rightblock, d.leftindex and d.rightindex
# become indices into distinct blocks and either may be larger than the
# other.

BLOCKLEN = 62
CENTER   = ((BLOCKLEN - 1) / 2)

class Block(object):
    __slots__ = ('leftlink', 'rightlink', 'data')
    def __init__(self, leftlink, rightlink):
        self.leftlink = leftlink
        self.rightlink = rightlink
        self.data = [None] * BLOCKLEN

# ------------------------------------------------------------

class W_Deque(Wrappable):
    def __init__(self, space):
        self.space = space
        self.clear()
        check_nonneg(self.leftindex)
        check_nonneg(self.rightindex)

    @unwrap_spec('self', W_Root)  #, W_Root)
    def init(self, w_iterable=NoneNotWrapped):  #, w_maxlen=None):
        if self.len > 0:
            self.clear()
        if w_iterable is not None:
            self.extend(w_iterable)

    @unwrap_spec('self', W_Root)
    def append(self, w_x):
        ri = self.rightindex + 1
        if ri >= BLOCKLEN:
            b = Block(self.rightblock, None)
            self.rightblock.rightlink = b
            self.rightblock = b
            ri = 0
        self.rightindex = ri
        self.rightblock.data[ri] = w_x
        self.len += 1

    @unwrap_spec('self', W_Root)
    def appendleft(self, w_x):
        li = self.leftindex - 1
        if li < 0:
            b = Block(None, self.leftblock)
            self.leftblock.leftlink = b
            self.leftblock = b
            li = BLOCKLEN - 1
        self.leftindex = li
        self.leftblock.data[li] = w_x
        self.len += 1

    @unwrap_spec('self')
    def clear(self):
        self.leftblock = Block(None, None)
        self.rightblock = self.leftblock
        self.leftindex = CENTER + 1
        self.rightindex = CENTER
        self.len = 0

    @unwrap_spec('self', W_Root)
    def extend(self, w_iterable):
        # XXX Handle case where id(deque) == id(iterable)
        space = self.space
        w_iter = space.iter(w_iterable)
        while True:
            try:
                w_obj = space.next(w_iter)
            except OperationError, e:
                if e.match(space, space.w_StopIteration):
                    break
                raise
            self.append(w_obj)

    @unwrap_spec('self', W_Root)
    def extendleft(self, w_iterable):
        # XXX Handle case where id(deque) == id(iterable)
        space = self.space
        w_iter = space.iter(w_iterable)
        while True:
            try:
                w_obj = space.next(w_iter)
            except OperationError, e:
                if e.match(space, space.w_StopIteration):
                    break
                raise
            self.appendleft(w_obj)

    @unwrap_spec('self')
    def pop(self):
        if self.len == 0:
            msg = "pop from an empty deque"
            raise OperationError(self.space.w_IndexError, self.space.wrap(msg))
        self.len -= 1
        ri = self.rightindex
        w_obj = self.rightblock.data[ri]
        ri -= 1
        if ri < 0:
            if self.len == 0:
                # re-center instead of freeing the last block
                self.leftindex = CENTER + 1
                ri = CENTER
            else:
                b = self.rightblock.leftlink
                self.rightblock = b
                b.rightlink = None
                ri = BLOCKLEN - 1
        self.rightindex = ri
        return w_obj

    @unwrap_spec('self')
    def popleft(self):
        if self.len == 0:
            msg = "pop from an empty deque"
            raise OperationError(self.space.w_IndexError, self.space.wrap(msg))
        self.len -= 1
        li = self.leftindex
        w_obj = self.leftblock.data[li]
        li += 1
        if li >= BLOCKLEN:
            if self.len == 0:
                # re-center instead of freeing the last block
                li = CENTER + 1
                self.rightindex = CENTER
            else:
                b = self.leftblock.rightlink
                self.leftblock = b
                b.leftlink = None
                li = 0
        self.leftindex = li
        return w_obj

    @unwrap_spec('self')
    def iter(self):
        return W_DequeIter(self)

    @unwrap_spec('self')
    def length(self):
        return self.space.wrap(self.len)


@unwrap_spec(ObjSpace, W_Root, Arguments)
def descr__new__(space, w_subtype, args):
    w_self = space.allocate_instance(W_Deque, w_subtype)
    W_Deque.__init__(space.interp_w(W_Deque, w_self), space)
    return w_self

W_Deque.typedef = TypeDef("deque",
    __new__ = interp2app(descr__new__),
    __init__ = interp2app(W_Deque.init),
    append     = interp2app(W_Deque.append),
    appendleft = interp2app(W_Deque.appendleft),
    clear      = interp2app(W_Deque.clear),
    extend     = interp2app(W_Deque.extend),
    extendleft = interp2app(W_Deque.extendleft),
    pop        = interp2app(W_Deque.pop),
    popleft    = interp2app(W_Deque.popleft),
    __weakref__ = make_weakref_descr(W_Deque),
    __iter__ = interp2app(W_Deque.iter),
    __len__ = interp2app(W_Deque.length),
)

# ------------------------------------------------------------

class W_DequeIter(Wrappable):
    def __init__(self, deque):
        self.space = deque.space
        self.deque = deque
        self.block = deque.leftblock
        self.index = deque.leftindex
        self.counter = deque.len
        check_nonneg(self.index)

    @unwrap_spec('self')
    def iter(self):
        return self.space.wrap(self)

    @unwrap_spec('self')
    def next(self):
        if self.counter == 0:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        self.counter -= 1
        ri = self.index
        w_x = self.block.data[ri]
        ri += 1
        if ri == BLOCKLEN:
            self.block = self.block.rightlink
            ri = 0
        self.index = ri
        return w_x

W_DequeIter.typedef = TypeDef("deque_iterator",
    __iter__ = interp2app(W_DequeIter.iter),
    next = interp2app(W_DequeIter.next),
)
W_DequeIter.typedef.acceptable_as_base_class = False

# ------------------------------------------------------------
