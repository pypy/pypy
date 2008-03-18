import sys
from pypy.interpreter.gateway import ObjSpace, W_Root, interp2app
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.error import OperationError
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.objectmodel import keepalive_until_here

from pypy.rlib import rzlib


if intmask(2**31) == -2**31:
    # 32-bit platforms
    unsigned_to_signed_32bit = intmask
else:
    # 64-bit platforms
    def unsigned_to_signed_32bit(x):
        # assumes that 'x' is in range(0, 2**32) to start with
        SIGN_EXTEND2 = 1 << 31
        return intmask((x ^ SIGN_EXTEND2) - SIGN_EXTEND2)


def crc32(space, string, start = rzlib.CRC32_DEFAULT_START):
    """
    crc32(string[, start]) -- Compute a CRC-32 checksum of string.

    An optional starting value can be specified.  The returned checksum is
    an integer.
    """
    checksum = rzlib.crc32(string, start)

    # This is, perhaps, a little stupid.  zlib returns the checksum unsigned.
    # CPython exposes it as a signed value, though. -exarkun
    # Note that in CPython < 2.6 on 64-bit platforms the result is
    # actually unsigned, but it was considered to be a bug so we stick to
    # the 2.6 behavior and always return a number in range(-2**31, 2**31).
    checksum = unsigned_to_signed_32bit(checksum)

    return space.wrap(checksum)
crc32.unwrap_spec = [ObjSpace, 'bufferstr', int]


def adler32(space, string, start = rzlib.ADLER32_DEFAULT_START):
    """
    adler32(string[, start]) -- Compute an Adler-32 checksum of string.

    An optional starting value can be specified.  The returned checksum is
    an integer.
    """
    checksum = rzlib.adler32(string, start)
    # See comments in crc32() for the following line
    checksum = unsigned_to_signed_32bit(checksum)

    return space.wrap(checksum)
adler32.unwrap_spec = [ObjSpace, 'bufferstr', int]


def zlib_error(space, msg):
    w_module = space.getbuiltinmodule('zlib')
    w_error = space.getattr(w_module, space.wrap('error'))
    return OperationError(w_error, space.wrap(msg))


def compress(space, string, level=rzlib.Z_DEFAULT_COMPRESSION):
    """
    compress(string[, level]) -- Returned compressed string.

    Optional arg level is the compression level, in 1-9.
    """
    try:
        try:
            stream = rzlib.deflateInit(level)
        except ValueError:
            raise zlib_error(space, "Bad compression level")
        try:
            result = rzlib.compress(stream, string, rzlib.Z_FINISH)
        finally:
            rzlib.deflateEnd(stream)
    except rzlib.RZlibError, e:
        raise zlib_error(space, e.msg)
    return space.wrap(result)
compress.unwrap_spec = [ObjSpace, 'bufferstr', int]


def decompress(space, string, wbits=rzlib.MAX_WBITS, bufsize=0):
    """
    decompress(string[, wbits[, bufsize]]) -- Return decompressed string.

    Optional arg wbits is the window buffer size.  Optional arg bufsize is
    only for compatibility with CPython and is ignored.
    """
    try:
        try:
            stream = rzlib.inflateInit(wbits)
        except ValueError:
            raise zlib_error(space, "Bad window buffer size")
        try:
            result, _, _ = rzlib.decompress(stream, string, rzlib.Z_FINISH)
        finally:
            rzlib.inflateEnd(stream)
    except rzlib.RZlibError, e:
        raise zlib_error(space, e.msg)
    return space.wrap(result)
decompress.unwrap_spec = [ObjSpace, 'bufferstr', int, int]


class ZLibObject(Wrappable):
    """
    Common base class for Compress and Decompress.
    """
    stream = rzlib.null_stream

    def __init__(self, space):
        self.space = space
        self._lock = space.allocate_lock()

    def lock(self):
        """To call before using self.stream."""
        self._lock.acquire(True)

    def unlock(self):
        """To call after using self.stream."""
        self._lock.release()
        keepalive_until_here(self)
        # subtle: we have to make sure that 'self' is not garbage-collected
        # while we are still using 'self.stream' - hence the keepalive.


class Compress(ZLibObject):
    """
    Wrapper around zlib's z_stream structure which provides convenient
    compression functionality.
    """
    def __init__(self, space, level=rzlib.Z_DEFAULT_COMPRESSION,
                 method=rzlib.Z_DEFLATED,             # \
                 wbits=rzlib.MAX_WBITS,               #  \   undocumented
                 memLevel=rzlib.DEF_MEM_LEVEL,        #  /    parameters
                 strategy=rzlib.Z_DEFAULT_STRATEGY):  # /
        ZLibObject.__init__(self, space)
        try:
            self.stream = rzlib.deflateInit(level, method, wbits,
                                            memLevel, strategy)
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("Invalid initialization option"))

    def __del__(self):
        """Automatically free the resources used by the stream."""
        if self.stream:
            rzlib.deflateEnd(self.stream)
            self.stream = rzlib.null_stream


    def compress(self, data):
        """
        compress(data) -- Return a string containing data compressed.

        After calling this function, some of the input data may still be stored
        in internal buffers for later processing.

        Call the flush() method to clear these buffers.
        """
        try:
            self.lock()
            try:
                if not self.stream:
                    raise zlib_error(self.space,
                                     "compressor object already flushed")
                result = rzlib.compress(self.stream, data)
            finally:
                self.unlock()
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        return self.space.wrap(result)
    compress.unwrap_spec = ['self', 'bufferstr']


    def flush(self, mode=rzlib.Z_FINISH):
        """
        flush( [mode] ) -- Return a string containing any remaining compressed
        data.

        mode can be one of the constants Z_SYNC_FLUSH, Z_FULL_FLUSH, Z_FINISH;
        the default value used when mode is not specified is Z_FINISH.

        If mode == Z_FINISH, the compressor object can no longer be used after
        calling the flush() method.  Otherwise, more data can still be
        compressed.
        """
        try:
            self.lock()
            try:
                if not self.stream:
                    raise zlib_error(self.space,
                                     "compressor object already flushed")
                result = rzlib.compress(self.stream, '', mode)
                if mode == rzlib.Z_FINISH:    # release the data structures now
                    rzlib.deflateEnd(self.stream)
                    self.stream = rzlib.null_stream
            finally:
                self.unlock()
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        return self.space.wrap(result)
    flush.unwrap_spec = ['self', int]


def Compress___new__(space, w_subtype, level=rzlib.Z_DEFAULT_COMPRESSION,
                     method=rzlib.Z_DEFLATED,             # \
                     wbits=rzlib.MAX_WBITS,               #  \   undocumented
                     memLevel=rzlib.DEF_MEM_LEVEL,        #  /    parameters
                     strategy=rzlib.Z_DEFAULT_STRATEGY):  # /
    """
    Create a new z_stream and call its initializer.
    """
    stream = space.allocate_instance(Compress, w_subtype)
    stream = space.interp_w(Compress, stream)
    Compress.__init__(stream, space, level,
                      method, wbits, memLevel, strategy)
    return space.wrap(stream)
Compress___new__.unwrap_spec = [ObjSpace, W_Root, int, int, int, int, int]


Compress.typedef = TypeDef(
    'Compress',
    __new__ = interp2app(Compress___new__),
    compress = interp2app(Compress.compress),
    flush = interp2app(Compress.flush),
    __doc__ = """compressobj([level]) -- Return a compressor object.

Optional arg level is the compression level, in 1-9.
""")


class Decompress(ZLibObject):
    """
    Wrapper around zlib's z_stream structure which provides convenient
    decompression functionality.
    """
    def __init__(self, space, wbits=rzlib.MAX_WBITS):
        """
        Initialize a new decompression object.

        wbits is an integer between 8 and MAX_WBITS or -8 and -MAX_WBITS
        (inclusive) giving the number of "window bits" to use for compression
        and decompression.  See the documentation for deflateInit2 and
        inflateInit2.
        """
        ZLibObject.__init__(self, space)
        self.unused_data = ''
        self.unconsumed_tail = ''
        try:
            self.stream = rzlib.inflateInit(wbits)
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("Invalid initialization option"))

    def __del__(self):
        """Automatically free the resources used by the stream."""
        if self.stream:
            rzlib.inflateEnd(self.stream)
            self.stream = rzlib.null_stream


    def decompress(self, data, max_length=0):
        """
        decompress(data[, max_length]) -- Return a string containing the
        decompressed version of the data.

        If the max_length parameter is specified then the return value will be
        no longer than max_length.  Unconsumed input data will be stored in the
        unconsumed_tail attribute.
        """
        if max_length == 0:
            max_length = sys.maxint
        elif max_length < 0:
            raise OperationError(self.space.w_ValueError,
                                 self.space.wrap("max_length must be "
                                                 "greater than zero"))
        try:
            self.lock()
            try:
                result = rzlib.decompress(self.stream, data,
                                          max_length = max_length)
            finally:
                self.unlock()
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)

        string, finished, unused_len = result
        unused_start = len(data) - unused_len
        assert unused_start >= 0
        tail = data[unused_start:]
        if finished:
            self.unconsumed_tail = ''
            self.unused_data = tail
        else:
            self.unconsumed_tail = tail
        return self.space.wrap(string)
    decompress.unwrap_spec = ['self', 'bufferstr', int]


    def flush(self, length=0):
        """
        flush( [length] ) -- This is kept for backward compatibility,
        because each call to decompress() immediately returns as much
        data as possible.
        """
        # We could call rzlib.decompress(self.stream, '', rzlib.Z_FINISH)
        # which would complain if the input stream so far is not complete;
        # however CPython's zlib module does not behave like that.
        # I could not figure out a case in which flush() in CPython
        # doesn't simply return an empty string without complaining.
        return self.space.wrap("")
    flush.unwrap_spec = ['self', int]


def Decompress___new__(space, w_subtype, wbits=rzlib.MAX_WBITS):
    """
    Create a new Decompress and call its initializer.
    """
    stream = space.allocate_instance(Decompress, w_subtype)
    stream = space.interp_w(Decompress, stream)
    Decompress.__init__(stream, space, wbits)
    return space.wrap(stream)
Decompress___new__.unwrap_spec = [ObjSpace, W_Root, int]


Decompress.typedef = TypeDef(
    'Decompress',
    __new__ = interp2app(Decompress___new__),
    decompress = interp2app(Decompress.decompress),
    flush = interp2app(Decompress.flush),
    unused_data = interp_attrproperty('unused_data', Decompress),
    unconsumed_tail = interp_attrproperty('unconsumed_tail', Decompress),
    __doc__ = """decompressobj([wbits]) -- Return a decompressor object.

Optional arg wbits is the window buffer size.
""")
