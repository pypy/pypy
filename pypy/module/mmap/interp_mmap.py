from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app, unwrap_spec, NoneNotWrapped
from pypy.rlib import rmmap
from pypy.rlib.rmmap import RValueError, RTypeError, ROverflowError
import sys
import os
import platform
import stat

class W_MMap(Wrappable):
    def __init__(self, space, mmap_obj):
        self.space = space
        self.mmap = mmap_obj
        
    def close(self):
        self.mmap.close()

    def read_byte(self):
        try:
            return self.space.wrap(self.mmap.read_byte())
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))

    def readline(self):
        return self.space.wrap(self.mmap.readline())

    @unwrap_spec(num=int)
    def read(self, num=-1):
        self.check_valid()
        return self.space.wrap(self.mmap.read(num))

    @unwrap_spec(tofind='bufferstr')
    def find(self, tofind, w_start=NoneNotWrapped, w_end=NoneNotWrapped):
        space = self.space
        if w_start is None:
            start = self.mmap.pos
        else:
            start = space.getindex_w(w_start, None)
        if w_end is None:
            end = self.mmap.size
        else:
            end = space.getindex_w(w_end, None)
        return space.wrap(self.mmap.find(tofind, start, end))

    @unwrap_spec(tofind='bufferstr')
    def rfind(self, tofind, w_start=NoneNotWrapped, w_end=NoneNotWrapped):
        space = self.space
        if w_start is None:
            start = self.mmap.pos
        else:
            start = space.getindex_w(w_start, None)
        if w_end is None:
            end = self.mmap.size
        else:
            end = space.getindex_w(w_end, None)
        return space.wrap(self.mmap.find(tofind, start, end, True))

    @unwrap_spec(pos='index', whence=int)
    def seek(self, pos, whence=0):
        try:
            self.mmap.seek(pos, whence)
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))

    def tell(self):
        return self.space.wrap(self.mmap.tell())

    def descr_size(self):
        try:
            return self.space.wrap(self.mmap.file_size())
        except OSError, e:
            raise mmap_error(self.space, e)

    @unwrap_spec(data='bufferstr')
    def write(self, data):
        self.check_writeable()
        try:
            self.mmap.write(data)
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))

    @unwrap_spec(byte=str)
    def write_byte(self, byte):
        try:
            self.mmap.write_byte(byte)
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))
        except RTypeError, v:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(v.message))

    @unwrap_spec(offset=int, size=int)
    def flush(self, offset=0, size=0):
        try:
            return self.space.wrap(self.mmap.flush(offset, size))
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))
        except OSError, e:
            raise mmap_error(self.space, e)

    @unwrap_spec(dest=int, src=int, count=int)
    def move(self, dest, src, count):
        try:
            self.mmap.move(dest, src, count)
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))

    @unwrap_spec(newsize=int)
    def resize(self, newsize):
        self.check_valid()
        self.check_resizeable()
        try:
            self.mmap.resize(newsize)
        except OSError, e:
            raise mmap_error(self.space, e)
        except RValueError, e:
            # obscure: in this case, RValueError translates to an app-level
            # SystemError.
            raise OperationError(self.space.w_SystemError,
                                 self.space.wrap(e.message))

    def __len__(self):
        return self.space.wrap(self.mmap.size)

    def check_valid(self):
        try:
            self.mmap.check_valid()
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))

    def check_writeable(self):
        try:
            self.mmap.check_writeable()
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))
        except RTypeError, v:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(v.message))

    def check_resizeable(self):
        try:
            self.mmap.check_resizeable()
        except RValueError, v:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap(v.message))
        except RTypeError, v:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap(v.message))

    def descr_getitem(self, w_index):
        self.check_valid()

        space = self.space
        start, stop, step = space.decode_index(w_index, self.mmap.size)
        if step == 0:  # index only
            return space.wrap(self.mmap.getitem(start))
        else:
            res = "".join([self.mmap.getitem(i)
                           for i in range(start, stop, step)])
            return space.wrap(res)

    def descr_setitem(self, w_index, w_value):
        space = self.space
        value = space.realstr_w(w_value)
        self.check_valid()

        self.check_writeable()

        start, stop, step, length = space.decode_index4(w_index, self.mmap.size)
        if step == 0:  # index only
            if len(value) != 1:
                raise OperationError(space.w_ValueError,
                                     space.wrap("mmap assignment must be "
                                                "single-character string"))
            self.mmap.setitem(start, value)
        else:
            if len(value) != length:
                raise OperationError(space.w_ValueError,
                          space.wrap("mmap slice assignment is wrong size"))
            for i in range(length):
                self.mmap.setitem(start, value[i])
                start += step

    def descr_buffer(self):
        # XXX improve to work directly on the low-level address
        from pypy.interpreter.buffer import StringLikeBuffer
        space = self.space
        return space.wrap(StringLikeBuffer(space, space.wrap(self)))

if rmmap._POSIX:

    @unwrap_spec(fileno=int, length='index', flags=int,
                 prot=int, access=int, offset='index')
    def mmap(space, w_subtype, fileno, length, flags=rmmap.MAP_SHARED,
             prot=rmmap.PROT_WRITE | rmmap.PROT_READ,
             access=rmmap._ACCESS_DEFAULT, offset=0):
        self = space.allocate_instance(W_MMap, w_subtype)
        try:
            W_MMap.__init__(self, space,
                            rmmap.mmap(fileno, length, flags, prot, access,
                                       offset))
        except OSError, e:
            raise mmap_error(space, e)
        except RValueError, e:
            raise OperationError(space.w_ValueError, space.wrap(e.message))
        except RTypeError, e:
            raise OperationError(space.w_TypeError, space.wrap(e.message))
        except ROverflowError, e:
            raise OperationError(space.w_OverflowError, space.wrap(e.message))
        return space.wrap(self)

elif rmmap._MS_WINDOWS:

    @unwrap_spec(fileno=int, length='index', tagname=str,
                 access=int, offset='index')
    def mmap(space, w_subtype, fileno, length, tagname="",
             access=rmmap._ACCESS_DEFAULT, offset=0):
        self = space.allocate_instance(W_MMap, w_subtype)
        try:
            W_MMap.__init__(self, space,
                            rmmap.mmap(fileno, length, tagname, access,
                                       offset))
        except OSError, e:
            raise mmap_error(space, e)
        except RValueError, e:
            raise OperationError(space.w_ValueError, space.wrap(e.message))
        except RTypeError, e:
            raise OperationError(space.w_TypeError, space.wrap(e.message))
        except ROverflowError, e:
            raise OperationError(space.w_OverflowError, space.wrap(e.message))
        return space.wrap(self)

W_MMap.typedef = TypeDef("mmap",
    __new__ = interp2app(mmap),
    close = interp2app(W_MMap.close),
    read_byte = interp2app(W_MMap.read_byte),
    readline = interp2app(W_MMap.readline),
    read = interp2app(W_MMap.read),
    find = interp2app(W_MMap.find),
    rfind = interp2app(W_MMap.rfind),
    seek = interp2app(W_MMap.seek),
    tell = interp2app(W_MMap.tell),
    size = interp2app(W_MMap.descr_size),
    write = interp2app(W_MMap.write),
    write_byte = interp2app(W_MMap.write_byte),
    flush = interp2app(W_MMap.flush),
    move = interp2app(W_MMap.move),
    resize = interp2app(W_MMap.resize),
    __module__ = "mmap",

    __len__ = interp2app(W_MMap.__len__),
    __getitem__ = interp2app(W_MMap.descr_getitem),
    __setitem__ = interp2app(W_MMap.descr_setitem),
    __buffer__ = interp2app(W_MMap.descr_buffer),
)

constants = rmmap.constants
PAGESIZE = rmmap.PAGESIZE
ALLOCATIONGRANULARITY = rmmap.ALLOCATIONGRANULARITY
ACCESS_READ  = rmmap.ACCESS_READ
ACCESS_WRITE = rmmap.ACCESS_WRITE
ACCESS_COPY  = rmmap.ACCESS_COPY

class Cache:
    def __init__(self, space):
        self.w_error = space.new_exception_class("mmap.error",
                                                 space.w_EnvironmentError)

def mmap_error(space, e):
    w_error = space.fromcache(Cache).w_error
    return wrap_oserror(space, e, w_exception_class=w_error)
