import sys
from pypy.interpreter import gateway
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.interpreter.typedef import GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError, oefmt
from rpython.rlib.debug import check_nonneg
from rpython.rlib.objectmodel import specialize


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

class W_Deque(W_Root):
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
            raise oefmt(self.space.w_RuntimeError,
                        "deque mutated during iteration")

    def init(self, w_iterable=None, w_maxlen=None):
        space = self.space
        if space.is_none(w_maxlen):
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

    def append(self, w_x):
        "Add an element to the right side of the deque."
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

    def appendleft(self, w_x):
        "Add an element to the left side of the deque."
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

    def clear(self):
        "Remove all elements from the deque."
        self.leftblock = Block(None, None)
        self.rightblock = self.leftblock
        self.leftindex = CENTER + 1
        self.rightindex = CENTER
        self.len = 0
        self.modified()

    def count(self, w_x):
        "Return number of occurrences of value."
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

    def extend(self, w_iterable):
        "Extend the right side of the deque with elements from the iterable"
        # Handle case where id(deque) == id(iterable)
        space = self.space
        if space.is_w(space.wrap(self), w_iterable):
            w_iterable = space.call_function(space.w_list, w_iterable)
        #
        w_iter = space.iter(w_iterable)
        while True:
            try:
                w_obj = space.next(w_iter)
            except OperationError as e:
                if e.match(space, space.w_StopIteration):
                    break
                raise
            self.append(w_obj)

    def add(self, w_iterable):
        copy = W_Deque(self.space)
        copy.extend(self.iter())
        copy.extend(w_iterable)
        return self.space.wrap(copy)

    def iadd(self, w_iterable):
        self.extend(w_iterable)
        return self.space.wrap(self)

    def mul(self, w_int):
        space = self.space
        copied = W_Deque(space)
        num = space.int_w(w_int)

        for _ in range(num):
            copied.extend(self)

        return space.wrap(copied)

    def rmul(self, w_int):
        return self.mul(w_int)

    def imul(self, w_int):
        space = self.space
        copy = W_Deque(space)
        copy.extend(self.iter())
        num = space.int_w(w_int)

        for _ in range(num - 1):
            self.extend(copy)

        return space.wrap(self)

    def extendleft(self, w_iterable):
        "Extend the left side of the deque with elements from the iterable"
        # Handle case where id(deque) == id(iterable)
        space = self.space
        if space.is_w(space.wrap(self), w_iterable):
            w_iterable = space.call_function(space.w_list, w_iterable)
        #
        w_iter = space.iter(w_iterable)
        while True:
            try:
                w_obj = space.next(w_iter)
            except OperationError as e:
                if e.match(space, space.w_StopIteration):
                    break
                raise
            self.appendleft(w_obj)

    def pop(self):
        "Remove and return the rightmost element."
        if self.len == 0:
            raise oefmt(self.space.w_IndexError, "pop from an empty deque")
        self.len -= 1
        ri = self.rightindex
        w_obj = self.rightblock.data[ri]
        self.rightblock.data[ri] = None
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

    def popleft(self):
        "Remove and return the leftmost element."
        if self.len == 0:
            raise oefmt(self.space.w_IndexError, "pop from an empty deque")
        self.len -= 1
        li = self.leftindex
        w_obj = self.leftblock.data[li]
        self.leftblock.data[li] = None
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

    def remove(self, w_x):
        "Remove first occurrence of value."
        space = self.space
        block = self.leftblock
        index = self.leftindex
        lock = self.getlock()
        for i in range(self.len):
            w_item = block.data[index]
            equal = space.eq_w(w_item, w_x)
            self.checklock(lock)
            if equal:
                self.del_item(i)
                return
            # Advance the block/index pair
            index += 1
            if index >= BLOCKLEN:
                block = block.rightlink
                index = 0
        raise oefmt(space.w_ValueError, "deque.remove(x): x not in deque")

    def reverse(self):
        "Reverse *IN PLACE*."
        li = self.leftindex
        lb = self.leftblock
        ri = self.rightindex
        rb = self.rightblock
        for i in range(self.len >> 1):
            lb.data[li], rb.data[ri] = rb.data[ri], lb.data[li]
            li += 1
            if li >= BLOCKLEN:
                lb = lb.rightlink
                li = 0
            ri -= 1
            if ri < 0:
                rb = rb.leftlink
                ri = BLOCKLEN - 1

    @unwrap_spec(n=int)
    def rotate(self, n=1):
        "Rotate the deque n steps to the right (default n=1).  If n is negative, rotates left."
        len = self.len
        if len <= 1:
            return
        halflen = len >> 1
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

    def iter(self):
        return W_DequeIter(self)

    def index(self, w_x, w_start=None, w_stop=None):
        space = self.space
        w_iter = space.iter(self)
        _len = self.len
        start = 0
        stop = _len
        lock = self.getlock()

        if w_start is not None:
            start = space.int_w(w_start)
            if start < 0:
                start += _len
            if start < 0:
                start = 0
            elif start > _len:
                start = _len

        if w_stop is not None:
            stop = space.int_w(w_stop)
            if stop < 0:
                stop += _len
            if 0 <= stop > _len:
                stop = _len

        for i in range(0, stop):
            try:
                w_obj = space.next(w_iter)
                if i < start:
                    continue
                if space.eq_w(w_obj, w_x):
                    return space.wrap(i)
                self.checklock(lock)
            except OperationError as e:
                if not e.match(space, space.w_StopIteration):
                    raise
        raise oefmt(space.w_ValueError, "%R is not in deque", w_x)

    @unwrap_spec(index=int)
    def insert(self, index, w_value):
        space = self.space
        n = space.len_w(self)
        if n == self.maxlen:
            raise oefmt(space.w_IndexError, "deque already at its maximum size")

        if index >= n:
            self.append(w_value)
        if index <= -n or index == 0:
            self.appendleft(w_value)

        self.rotate(-index)
        if index < 0:
            self.append(w_value)
        else:
            self.appendleft(w_value)
        self.rotate(index)

    def reviter(self):
        "Return a reverse iterator over the deque."
        return W_DequeRevIter(self)

    def length(self):
        return self.space.wrap(self.len)

    def repr(self):
        space = self.space
        ec = space.getexecutioncontext()
        w_currently_in_repr = ec._py_repr
        if w_currently_in_repr is None:
            w_currently_in_repr = ec._py_repr = space.newdict()
        return dequerepr(space, w_currently_in_repr, space.wrap(self))

    @specialize.arg(2)
    def compare(self, w_other, op):
        space = self.space
        if not isinstance(w_other, W_Deque):
            return space.w_NotImplemented
        return space.compare_by_iteration(space.wrap(self), w_other, op)

    def lt(self, w_other):
        return self.compare(w_other, 'lt')
    def le(self, w_other):
        return self.compare(w_other, 'le')
    def eq(self, w_other):
        return self.compare(w_other, 'eq')
    def ne(self, w_other):
        return self.compare(w_other, 'ne')
    def gt(self, w_other):
        return self.compare(w_other, 'gt')
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

    def del_item(self, i):
        # delitem() implemented in terms of rotate for simplicity and
        # reasonable performance near the end points.
        self.rotate(-i)
        self.popleft()
        self.rotate(i)

    def getitem(self, w_index):
        space = self.space
        start, stop, step = space.decode_index(w_index, self.len)
        if step == 0:  # index only
            b, i = self.locate(start)
            return b.data[i]
        else:
            raise oefmt(space.w_TypeError, "deque[:] is not supported")

    def setitem(self, w_index, w_newobj):
        space = self.space
        start, stop, step = space.decode_index(w_index, self.len)
        if step == 0:  # index only
            b, i = self.locate(start)
            b.data[i] = w_newobj
        else:
            raise oefmt(space.w_TypeError, "deque[:] is not supported")

    def delitem(self, w_index):
        space = self.space
        start, stop, step = space.decode_index(w_index, self.len)
        if step == 0:  # index only
            self.del_item(start)
        else:
            raise oefmt(space.w_TypeError, "deque[:] is not supported")

    def copy(self):
        "Return a shallow copy of a deque."
        space = self.space
        if self.maxlen == sys.maxint:
            return space.call_function(space.type(self), self)
        else:
            return space.call_function(space.type(self), self,
                                       space.wrap(self.maxlen))

    def reduce(self):
        "Return state information for pickling."
        space = self.space
        w_type = space.type(self)
        w_dict = space.findattr(self, space.wrap('__dict__'))
        w_list = space.call_function(space.w_list, self)
        if w_dict is None:
            if self.maxlen == sys.maxint:
                result = [
                    w_type, space.newtuple([w_list])]
            else:
                result = [
                    w_type, space.newtuple([w_list, space.wrap(self.maxlen)])]
        else:
            if self.maxlen == sys.maxint:
                w_len = space.w_None
            else:
                w_len = space.wrap(self.maxlen)
            result = [
                w_type, space.newtuple([w_list, w_len]), w_dict]
        return space.newtuple(result)

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


def descr__new__(space, w_subtype, __args__):
    w_self = space.allocate_instance(W_Deque, w_subtype)
    W_Deque.__init__(space.interp_w(W_Deque, w_self), space)
    return w_self

W_Deque.typedef = TypeDef("collections.deque",
    __doc__ = """deque(iterable[, maxlen]) --> deque object

Build an ordered collection accessible from endpoints only.""",
    __new__ = interp2app(descr__new__),
    __init__ = interp2app(W_Deque.init),
    append     = interp2app(W_Deque.append),
    appendleft = interp2app(W_Deque.appendleft),
    clear      = interp2app(W_Deque.clear),
    count      = interp2app(W_Deque.count),
    extend     = interp2app(W_Deque.extend),
    extendleft = interp2app(W_Deque.extendleft),
    index      = interp2app(W_Deque.index),
    insert     = interp2app(W_Deque.insert),
    pop        = interp2app(W_Deque.pop),
    popleft    = interp2app(W_Deque.popleft),
    remove     = interp2app(W_Deque.remove),
    reverse    = interp2app(W_Deque.reverse),
    rotate     = interp2app(W_Deque.rotate),
    copy       = interp2app(W_Deque.copy),
    __weakref__ = make_weakref_descr(W_Deque),
    __iter__ = interp2app(W_Deque.iter),
    __reversed__ = interp2app(W_Deque.reviter),
    __len__ = interp2app(W_Deque.length),
    __repr__ = interp2app(W_Deque.repr),
    __lt__ = interp2app(W_Deque.lt),
    __le__ = interp2app(W_Deque.le),
    __eq__ = interp2app(W_Deque.eq),
    __ne__ = interp2app(W_Deque.ne),
    __gt__ = interp2app(W_Deque.gt),
    __ge__ = interp2app(W_Deque.ge),
    __hash__ = None,
    __add__ = interp2app(W_Deque.add),
    __iadd__ = interp2app(W_Deque.iadd),
    __getitem__ = interp2app(W_Deque.getitem),
    __setitem__ = interp2app(W_Deque.setitem),
    __delitem__ = interp2app(W_Deque.delitem),
    __copy__ = interp2app(W_Deque.copy),
    __reduce__ = interp2app(W_Deque.reduce),
    __mul__ = interp2app(W_Deque.mul),
    __imul__ = interp2app(W_Deque.imul),
    __rmul__ = interp2app(W_Deque.rmul),
    maxlen = GetSetProperty(W_Deque.get_maxlen),
)

# ------------------------------------------------------------

class W_DequeIter(W_Root):
    def __init__(self, deque):
        self.space = deque.space
        self.deque = deque
        self.block = deque.leftblock
        self.index = deque.leftindex
        self.counter = deque.len
        self.lock = deque.getlock()
        check_nonneg(self.index)

    def iter(self):
        return self.space.wrap(self)

    def length(self):
        return self.space.wrap(self.counter)

    def next(self):
        space = self.space
        if self.lock is not self.deque.lock:
            self.counter = 0
            raise oefmt(space.w_RuntimeError, "deque mutated during iteration")
        if self.counter == 0:
            raise OperationError(space.w_StopIteration, space.w_None)
        self.counter -= 1
        ri = self.index
        w_x = self.block.data[ri]
        ri += 1
        if ri == BLOCKLEN:
            self.block = self.block.rightlink
            ri = 0
        self.index = ri
        return w_x

    def reduce(self):
        return self.space.newtuple([self.space.gettypefor(W_DequeIter),
                                    self.space.newtuple([self.deque])])

def W_DequeIter__new__(space, w_subtype, w_deque):
    w_self = space.allocate_instance(W_DequeIter, w_subtype)
    if not isinstance(w_deque, W_Deque):
        raise oefmt(space.w_TypeError, "must be collections.deque, not %T", w_deque)

    W_DequeIter.__init__(space.interp_w(W_DequeIter, w_self), w_deque)
    return w_self

W_DequeIter.typedef = TypeDef("_collections.deque_iterator",
    __new__ = interp2app(W_DequeIter__new__),
    __iter__        = interp2app(W_DequeIter.iter),
    __length_hint__ = interp2app(W_DequeIter.length),
    __next__        = interp2app(W_DequeIter.next),
    __reduce__      = interp2app(W_DequeIter.reduce)
)
W_DequeIter.typedef.acceptable_as_base_class = False

# ------------------------------------------------------------

class W_DequeRevIter(W_Root):
    def __init__(self, deque):
        self.space = deque.space
        self.deque = deque
        self.block = deque.rightblock
        self.index = deque.rightindex
        self.counter = deque.len
        self.lock = deque.getlock()
        check_nonneg(self.index)

    def iter(self):
        return self.space.wrap(self)

    def length(self):
        return self.space.wrap(self.counter)

    def next(self):
        space = self.space
        if self.lock is not self.deque.lock:
            self.counter = 0
            raise oefmt(space.w_RuntimeError, "deque mutated during iteration")
        if self.counter == 0:
            raise OperationError(space.w_StopIteration, space.w_None)
        self.counter -= 1
        ri = self.index
        w_x = self.block.data[ri]
        ri -= 1
        if ri < 0:
            self.block = self.block.leftlink
            ri = BLOCKLEN - 1
        self.index = ri
        return w_x

    def reduce(self):
        return self.space.newtuple([self.space.gettypefor(W_DequeRevIter),
                                    self.space.newtuple([self.deque])])

def W_DequeRevIter__new__(space, w_subtype, w_deque):
    w_self = space.allocate_instance(W_DequeRevIter, w_subtype)
    if not isinstance(w_deque, W_Deque):
        raise oefmt(space.w_TypeError, "must be collections.deque, not %T", w_deque)

    W_DequeRevIter.__init__(space.interp_w(W_DequeRevIter, w_self), w_deque)
    return w_self

W_DequeRevIter.typedef = TypeDef("_collections.deque_reverse_iterator",
    __new__         = interp2app(W_DequeRevIter__new__),
    __iter__        = interp2app(W_DequeRevIter.iter),
    __length_hint__ = interp2app(W_DequeRevIter.length),
    __next__        = interp2app(W_DequeRevIter.next),
    __reduce__      = interp2app(W_DequeRevIter.reduce)
)
W_DequeRevIter.typedef.acceptable_as_base_class = False

# ------------------------------------------------------------
