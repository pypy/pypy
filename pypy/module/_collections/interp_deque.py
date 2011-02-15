from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp2app, make_weakref_descr
from pypy.interpreter.gateway import ObjSpace, W_Root, Arguments


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
    def __init__(self, leftlink, rightlink):
        self.leftlink = leftlink
        self.rightlink = rightlink
        self.data = [None] * BLOCKLEN


class W_Deque(Wrappable):
    def __init__(self, space):
        self.space = space
        self.len = 0
        self.leftblock = self.rightblock = Block(None, None)
        self.leftindex = CENTER + 1
        self.rightindex = CENTER

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
    append.unwrap_spec = ['self', W_Root]

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
    appendleft.unwrap_spec = ['self', W_Root]


def descr__new__(space, w_subtype, args):
    w_self = space.allocate_instance(W_Deque, w_subtype)
    W_Deque.__init__(space.interp_w(W_Deque, w_self), space)
    return w_self
descr__new__.unwrap_spec = [ObjSpace, W_Root, Arguments]

W_Deque.typedef = TypeDef("deque",
    __new__ = interp2app(descr__new__),
    append = interp2app(W_Deque.append),
    appendleft = interp2app(W_Deque.appendleft),
    __weakref__ = make_weakref_descr(W_Deque),
)
