from pypy.interpreter.typedef import (
    TypeDef, generic_new_descr)
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.module._io.interp_iobase import W_IOBase
from pypy.module._io.interp_io import DEFAULT_BUFFER_SIZE
from pypy.module.thread.os_lock import Lock

class W_BufferedIOBase(W_IOBase):
    def __init__(self, space):
        W_IOBase.__init__(self, space)
        self.buffer = lltype.nullptr(rffi.CCHARP.TO)
        self.lock = None

    def _init(self, space):
        if self.buffer_size <= 0:
            raise OperationError(space.w_ValueError, space.wrap(
                "buffer size must be strictly positive"))

        if self.buffer:
            lltype.free(self.buffer, flavor='raw')
        self.buffer = lltype.malloc(rffi.CCHARP.TO, self.buffer_size,
                                    flavor='raw')

        ## XXX cannot free a Lock?
        ## if self.lock:
        ##     self.lock.free()
        self.lock = Lock(space)

        try:
            self._raw_tell(space)
        except OperationError:
            pass

    def _raw_tell(self, space):
        w_pos = space.call_method(self.raw, "tell")
        pos = space.r_longlong_w(w_pos)
        if pos < 0:
            raise OperationError(space.w_IOError, space.wrap(
                "raw stream returned invalid position"))

        self.abs_pos = pos
        return pos

W_BufferedIOBase.typedef = TypeDef(
    '_BufferedIOBase', W_IOBase.typedef,
    __new__ = generic_new_descr(W_BufferedIOBase),
    )

class W_BufferedReader(W_BufferedIOBase):
    def __init__(self, space):
        W_BufferedIOBase.__init__(self, space)
        self.ok = False
        self.detached = False

    @unwrap_spec('self', ObjSpace, W_Root, int)
    def descr_init(self, space, w_raw, buffer_size=DEFAULT_BUFFER_SIZE):
        raw = space.interp_w(W_IOBase, w_raw)
        raw.check_readable_w(space)

        self.raw = raw
        self.buffer_size = buffer_size
        self.readable = True
        self.writable = False

        self._init(space)
        self._reset_buf()

    def _reset_buf(self):
        self.read_end = -1

W_BufferedReader.typedef = TypeDef(
    'BufferedReader', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedReader),
    __init__  = interp2app(W_BufferedReader.descr_init),
    )

class W_BufferedWriter(W_BufferedIOBase):
    pass
W_BufferedWriter.typedef = TypeDef(
    'BufferedWriter', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedWriter),
    )

class W_BufferedRWPair(W_BufferedIOBase):
    pass
W_BufferedRWPair.typedef = TypeDef(
    'BufferedRWPair', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedRWPair),
    )

class W_BufferedRandom(W_BufferedIOBase):
    pass
W_BufferedRandom.typedef = TypeDef(
    'BufferedRandom', W_BufferedIOBase.typedef,
    __new__ = generic_new_descr(W_BufferedRandom),
    )

