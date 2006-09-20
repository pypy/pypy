from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, interp2app
from pypy.interpreter.baseobjspace import Wrappable
from pypy.rpython.rarithmetic import r_uint
from pypy.module._random import rpy_random

import time

def descr_new__(space, w_subtype, w_anything=None):
    x = space.allocate_instance(W_Random, w_subtype)
    W_Random.__init__(x, space, w_anything)
    return space.wrap(x)

class W_Random(Wrappable):
    def __init__(self, space, w_anything):
        self._rnd = rpy_random.Random()
        self.seed(space, w_anything)
    __init__.unwrap_spec = ['self', ObjSpace, W_Root]

    def random(self, space):
        return space.newfloat(self._rnd.random())
    random.unwrap_spec = ['self', ObjSpace]

    def seed(self, space, w_n=None):
        if w_n is None:
            w_n = space.newint(int(time.time()))
        else:
            if space.is_true(space.isinstance(w_n, space.w_int)):
                w_n = space.abs(w_n)
            elif space.is_true(space.isinstance(w_n, space.w_long)):
                w_n = space.abs(w_n)
            else:
                # XXX not perfectly like CPython
                w_n = space.abs(space.hash(w_n))
        key = []
        w_one = space.newlong(1)
        w_two = space.newlong(2)
        w_thirtytwo = space.newlong(32)
        # 0xffffffff
        w_masklower = space.sub(space.pow(w_two, w_thirtytwo, space.w_None),
                                w_one)
        while space.is_true(w_n):
            w_chunk = space.and_(w_n, w_masklower)
            chunk = space.uint_w(w_chunk)
            key.append(chunk)
            w_n = space.rshift(w_n, w_thirtytwo)
        if not key:
            key = [r_uint(0)]
        self._rnd.init_by_array(key)
    seed.unwrap_spec = ['self', ObjSpace, W_Root]

    def getstate(self, space):
        state = [None] * (rpy_random.N + 1)
        for i in range(rpy_random.N):
            state[i] = space.newlong(int(self._rnd.state[i]))
        state[rpy_random.N] = space.newint(self._rnd.index)
        return space.newtuple(state)
    getstate.unwrap_spec = ['self', ObjSpace]

    def setstate(self, space, w_state):
        if not space.is_true(space.isinstance(w_state, space.w_tuple)):
            errstring = space.wrap("state vector must be tuple")
            raise OperationError(space.w_TypeError, errstring)
        if space.int_w(space.len(w_state)) != rpy_random.N + 1:
            errstring = space.wrap("state vector is the wrong size")
            raise OperationError(space.w_ValueError, errstring)
        w_zero = space.newint(0)
        # independent of platfrom, since the below condition is only
        # true on 32 bit platforms anyway
        w_add = space.pow(space.newint(2), space.newint(32), space.w_None)
        for i in range(rpy_random.N):
            w_item = space.getitem(w_state, space.newint(i))
            if space.is_true(space.lt(w_item, w_zero)):
                w_item = space.add(w_item, w_add)
            self._rnd.state[i] = space.uint_w(w_item)
        w_item = space.getitem(w_state, space.newint(rpy_random.N))
        self._rnd.index = space.int_w(w_item)
    setstate.unwrap_spec = ['self', ObjSpace, W_Root]

    def jumpahead(self, n):
        self._rnd.jumpahead(n)
    jumpahead.unwrap_spec = ['self', int]

    def getrandbits(self, space, k):
        if k <= 0:
            strerror = space.wrap("number of bits must be greater than zero")
            raise OperationError(space.w_ValueError, strerror)
        bytes = ((k - 1) // 32 + 1) * 4
        bytesarray = [0] * bytes
        for i in range(0, bytes, 4):
            r = self._rnd.genrand32()
            if k < 32:
                r >>= (32 - k)
            bytesarray[i + 0] = r & r_uint(0xff)
            bytesarray[i + 1] = (r >> 8) & r_uint(0xff)
            bytesarray[i + 2] = (r >> 16) & r_uint(0xff)
            bytesarray[i + 3] = (r >> 24) & r_uint(0xff)
            k -= 32
        print bytesarray

        # XXX so far this is quadratic
        w_result = space.newlong(0)
        w_eight = space.newlong(8)
        for i in range(len(bytesarray) - 1, -1, -1):
            byte = bytesarray[i]
            w_result = space.or_(space.lshift(w_result, w_eight),
                                 space.newlong(int(byte)))
        return w_result
    getrandbits.unwrap_spec = ['self', ObjSpace, int]


W_Random.typedef = TypeDef("W_Random",
    __new__ = interp2app(descr_new__),
    random = interp2app(W_Random.random),
    seed = interp2app(W_Random.seed),
    getstate = interp2app(W_Random.getstate),
    setstate = interp2app(W_Random.setstate),
    jumpahead = interp2app(W_Random.jumpahead),
    getrandbits = interp2app(W_Random.getrandbits),
)
