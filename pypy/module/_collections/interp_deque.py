import sys
from pypy.interpreter import gateway
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp2app, make_weakref_descr
from pypy.interpreter.typedef import GetSetProperty
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

class Lock(object):
    pass

# ------------------------------------------------------------

class W_Deque(Wrappable):
    def __init__(self, space):
        self.space = space
        self.maxlen = sys.maxint
        self.clear()
        check_nonneg(self.leftindex)
        check_nonneg(self.rightindex)
        #
        # lightweight locking: any modification to the content of the deque
        # sets the lock to None.  Taking an iterator sets it to a non-None
        # value.  The iterator can check if further modifications occurred
        # by checking if the lock still has the same non-None value.
        # (In CPython, this is implemented using d->state.)
        self.lock = None

    def modified(self):
        self.lock = None

    def getlock(self):
        if self.lock is None:
            self.lock = Lock()
        return self.lock

    def checklock(self, lock):
        if lock is not self.lock:
            raise OperationError(
                self.space.w_RuntimeError,
                self.space.wrap("deque mutated during iteration"))

    @unwrap_spec('self', W_Root, W_Root)
    def init(self, w_iterable=NoneNotWrapped, w_maxlen=None):
        space = self.space
        if space.is_w(w_maxlen, space.w_None):
            maxlen = sys.maxint
        else:
            maxlen = space.gateway_nonnegint_w(w_maxlen)
        self.maxlen = maxlen
        if self.len > 0:
            self.clear()
        if w_iterable is not None:
            self.extend(w_iterable)

    def trimleft(self):
        if self.len > self.maxlen:
            self.popleft()
            assert self.len == self.maxlen

    def trimright(self):
        if self.len > self.maxlen:
            self.pop()
            assert self.len == self.maxlen

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
        self.trimleft()
        self.modified()

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
        self.trimright()
        self.modified()

    @unwrap_spec('self')
    def clear(self):
        self.leftblock = Block(None, None)
        self.rightblock = self.leftblock
        self.leftindex = CENTER + 1
        self.rightindex = CENTER
        self.len = 0
        self.modified()

    @unwrap_spec('self', W_Root)
    def count(self, w_x):
        space = self.space
        result = 0
        block = self.leftblock
        index = self.leftindex
        lock = self.getlock()
        for i in range(self.len):
            w_item = block.data[index]
            if space.eq_w(w_item, w_x):
                result += 1
            self.checklock(lock)
            # Advance the block/index pair
            index += 1
            if index >= BLOCKLEN:
                block = block.rightlink
                index = 0
        return space.wrap(result)

    @unwrap_spec('self', W_Root)
    def extend(self, w_iterable):
        # Handle case where id(deque) == id(iterable)
        space = self.space
        if space.is_w(space.wrap(self), w_iterable):
            w_iterable = space.call_function(space.w_list, w_iterable)
        #
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
    def iadd(self, w_iterable):
        self.extend(w_iterable)
        return self.space.wrap(self)

    @unwrap_spec('self', W_Root)
    def extendleft(self, w_iterable):
        # Handle case where id(deque) == id(iterable)
        space = self.space
        if space.is_w(space.wrap(self), w_iterable):
            w_iterable = space.call_function(space.w_list, w_iterable)
        #
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
        self.modified()
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
        self.modified()
        return w_obj

    @unwrap_spec('self')
    def reverse(self):
        li = self.leftindex
        lb = self.leftblock
        ri = self.rightindex
        rb = self.rightblock
        while lb is not rb or li < ri:
            lb.data[li], rb.data[ri] = rb.data[ri], lb.data[li]
            li += 1
            if li >= BLOCKLEN:
                lb = lb.rightlink
                li = 0
            ri -= 1
            if ri < 0:
                rb = rb.leftlink
                ri = BLOCKLEN - 1

    @unwrap_spec('self', int)
    def rotate(self, n=1):
        len = self.len
        if len == 0:
            return
        halflen = (len+1) >> 1
        if n > halflen or n < -halflen:
            n %= len
            if n > halflen:
                n -= len
        i = 0
        while i < n:
            self.appendleft(self.pop())
            i += 1
        while i > n:
            self.append(self.popleft())
            i -= 1

    @unwrap_spec('self')
    def iter(self):
        return W_DequeIter(self)

    @unwrap_spec('self')
    def length(self):
        return self.space.wrap(self.len)

    @unwrap_spec('self')
    def repr(self):
        space = self.space
        ec = space.getexecutioncontext()
        w_currently_in_repr = ec._py_repr
        if w_currently_in_repr is None:
            w_currently_in_repr = ec._py_repr = space.newdict()
        return dequerepr(space, w_currently_in_repr, space.wrap(self))

    def compare(self, w_other, op):
        space = self.space
        if not isinstance(space.interpclass_w(w_other), W_Deque):
            return space.w_NotImplemented
        return space.compare_by_iteration(space.wrap(self), w_other, op)
    compare._annspecialcase_ = 'specialize:arg(2)'

    @unwrap_spec('self', W_Root)
    def lt(self, w_other):
        return self.compare(w_other, 'lt')
    @unwrap_spec('self', W_Root)
    def le(self, w_other):
        return self.compare(w_other, 'le')
    @unwrap_spec('self', W_Root)
    def eq(self, w_other):
        return self.compare(w_other, 'eq')
    @unwrap_spec('self', W_Root)
    def ne(self, w_other):
        return self.compare(w_other, 'ne')
    @unwrap_spec('self', W_Root)
    def gt(self, w_other):
        return self.compare(w_other, 'gt')
    @unwrap_spec('self', W_Root)
    def ge(self, w_other):
        return self.compare(w_other, 'ge')

    def locate(self, i):
        if i < (self.len >> 1):
            i += self.leftindex
            b = self.leftblock
            while i >= BLOCKLEN:
                b = b.rightlink
                i -= BLOCKLEN
        else:
            i = i - self.len + 1     # then i <= 0
            i += self.rightindex
            b = self.rightblock
            while i < 0:
                b = b.leftlink
                i += BLOCKLEN
        assert i >= 0
        return b, i

    @unwrap_spec('self', W_Root)
    def getitem(self, w_index):
        space = self.space
        start, stop, step = space.decode_index(w_index, self.len)
        if step == 0:  # index only
            b, i = self.locate(start)
            return b.data[i]
        else:
            raise OperationError(self.w_TypeError,
                                 self.wrap("deque[:] is not supported"))

    @unwrap_spec('self', W_Root, W_Root)
    def setitem(self, w_index, w_newobj):
        space = self.space
        start, stop, step = space.decode_index(w_index, self.len)
        if step == 0:  # index only
            b, i = self.locate(start)
            b.data[i] = w_newobj
        else:
            raise OperationError(self.w_TypeError,
                                 self.wrap("deque[:] is not supported"))

    @unwrap_spec('self', W_Root)
    def delitem(self, w_index):
        space = self.space
        start, stop, step = space.decode_index(w_index, self.len)
        if step == 0:  # index only
            # delitem() implemented in terms of rotate for simplicity and
            # reasonable performance near the end points.
            i = start
            self.rotate(-i)
            self.popleft()
            self.rotate(i)
        else:
            raise OperationError(self.w_TypeError,
                                 self.wrap("deque[:] is not supported"))

    def get_maxlen(space, self):
        if self.maxlen == sys.maxint:
            return self.space.w_None
        else:
            return self.space.wrap(self.maxlen)


app = gateway.applevel("""
    def dequerepr(currently_in_repr, d):
        'The app-level part of repr().'
        deque_id = id(d)
        if deque_id in currently_in_repr:
            listrepr = '[...]'
        else:
            currently_in_repr[deque_id] = 1
            try:
                listrepr = "[" + ", ".join([repr(x) for x in d]) + ']'
            finally:
                try:
                    del currently_in_repr[deque_id]
                except:
                    pass
        if d.maxlen is None:
            maxlenrepr = ''
        else:
            maxlenrepr = ', maxlen=%d' % (d.maxlen,)
        return 'deque(%s%s)' % (listrepr, maxlenrepr)
""", filename=__file__)

dequerepr = app.interphook("dequerepr")


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
    count      = interp2app(W_Deque.count),
    extend     = interp2app(W_Deque.extend),
    extendleft = interp2app(W_Deque.extendleft),
    pop        = interp2app(W_Deque.pop),
    popleft    = interp2app(W_Deque.popleft),
    reverse    = interp2app(W_Deque.reverse),
    rotate     = interp2app(W_Deque.rotate),
    __weakref__ = make_weakref_descr(W_Deque),
    __iter__ = interp2app(W_Deque.iter),
    __len__ = interp2app(W_Deque.length),
    __repr__ = interp2app(W_Deque.repr),
    __lt__ = interp2app(W_Deque.lt),
    __le__ = interp2app(W_Deque.le),
    __eq__ = interp2app(W_Deque.eq),
    __ne__ = interp2app(W_Deque.ne),
    __gt__ = interp2app(W_Deque.gt),
    __ge__ = interp2app(W_Deque.ge),
    __iadd__ = interp2app(W_Deque.iadd),
    __getitem__ = interp2app(W_Deque.getitem),
    __setitem__ = interp2app(W_Deque.setitem),
    __delitem__ = interp2app(W_Deque.delitem),
    maxlen = GetSetProperty(W_Deque.get_maxlen),
)

# ------------------------------------------------------------

class W_DequeIter(Wrappable):
    def __init__(self, deque):
        self.space = deque.space
        self.deque = deque
        self.block = deque.leftblock
        self.index = deque.leftindex
        self.counter = deque.len
        self.lock = deque.getlock()
        check_nonneg(self.index)

    @unwrap_spec('self')
    def iter(self):
        return self.space.wrap(self)

    @unwrap_spec('self')
    def next(self):
        self.deque.checklock(self.lock)
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
