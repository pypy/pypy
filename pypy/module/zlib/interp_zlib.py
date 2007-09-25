from pypy.interpreter.gateway import ObjSpace, W_Root, interp2app
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.error import OperationError

from pypy.rlib import rzlib


def crc32(space, string, start = rzlib.CRC32_DEFAULT_START):
    """
    crc32(string[, start]) -- Compute a CRC-32 checksum of string.

    An optional starting value can be specified.  The returned checksum is
    an integer.
    """
    checksum = rzlib.crc32(string, start)

    # This is, perhaps, a little stupid.  zlib returns the checksum unsigned.
    # CPython exposes it as a signed value, though. -exarkun
    # The value *is* unsigned on 64-bit platforms in CPython... bah.
    # For now let's do the same as CPython and boldly cast to a C long. -arigo
    checksum = int(checksum)

    return space.wrap(checksum)
crc32.unwrap_spec = [ObjSpace, str, int]


def adler32(space, string, start = rzlib.ADLER32_DEFAULT_START):
    """
    adler32(string[, start]) -- Compute an Adler-32 checksum of string.

    An optional starting value can be specified.  The returned checksum is
    an integer.
    """
    checksum = rzlib.adler32(string, start)

    # This is, perhaps, a little stupid.  zlib returns the checksum unsigned.
    # CPython exposes it as a signed value, though. -exarkun
    # The value *is* unsigned on 64-bit platforms in CPython... bah.
    # For now let's do the same as CPython and boldly cast to a C long. -arigo
    checksum = int(checksum)

    return space.wrap(checksum)
adler32.unwrap_spec = [ObjSpace, str, int]


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
            raise OperationError(space.w_ValueError,
                                 space.wrap("Invalid initialization option"))
        try:
            result = rzlib.compress(stream, string, rzlib.Z_FINISH)
        finally:
            rzlib.deflateEnd(stream)
    except rzlib.RZlibError, e:
        raise zlib_error(space, e.msg)
    return space.wrap(result)
compress.unwrap_spec = [ObjSpace, str, int]


def decompress(space, string, wbits=rzlib.MAX_WBITS, bufsize=0):
    """
    decompress(string[, wbits[, bufsize]]) -- Return decompressed string.

    Optional arg wbits is the window buffer size.  Optional arg bufsize is
    the initial output buffer size.
    """
    try:
        try:
            stream = rzlib.inflateInit(wbits)
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("Invalid initialization option"))
        try:
            result = rzlib.decompress(stream, string, rzlib.Z_FINISH)
        finally:
            rzlib.inflateEnd(stream)
    except rzlib.RZlibError, e:
        raise zlib_error(space, e.msg)
    return space.wrap(result)
decompress.unwrap_spec = [ObjSpace, str, int, int]


class Compress(Wrappable):
    """
    Wrapper around zlib's z_stream structure which provides convenient
    compression functionality.
    """
    stream = rzlib.null_stream

    def __init__(self, space, level=rzlib.Z_DEFAULT_COMPRESSION):
        # XXX CPython actually exposes 4 more undocumented parameters beyond
        # level.
        self.space = space
        try:
            self.stream = rzlib.deflateInit(level)
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        except ValueError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("Invalid initialization option"))

    def __del__(self):
        """Automatically free the resources used by the stream."""
        if self.stream:
            rzlib.deflateEnd(self.stream)
            self.stream = null_stream


    def compress(self, data):
        """
        compress(data) -- Return a string containing data compressed.

        After calling this function, some of the input data may still be stored
        in internal buffers for later processing.

        Call the flush() method to clear these buffers.
        """
        try:
            result = rzlib.compress(self.stream, data)
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        return self.space.wrap(result)
    compress.unwrap_spec = ['self', str]


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
            result = rzlib.compress(self.stream, '', mode)
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        return self.space.wrap(result)
    flush.unwrap_spec = ['self', int]


def Compress___new__(space, w_subtype, level=rzlib.Z_DEFAULT_COMPRESSION):
    """
    Create a new z_stream and call its initializer.
    """
    stream = space.allocate_instance(Compress, w_subtype)
    stream = space.interp_w(Compress, stream)
    Compress.__init__(stream, space, level)
    return space.wrap(stream)
Compress___new__.unwrap_spec = [ObjSpace, W_Root, int]


Compress.typedef = TypeDef(
    'Compress',
    __new__ = interp2app(Compress___new__),
    compress = interp2app(Compress.compress),
    flush = interp2app(Compress.flush),
    __doc__ = """compressobj([level]) -- Return a compressor object.

Optional arg level is the compression level, in 1-9.
""")


class Decompress(Wrappable):
    """
    Wrapper around zlib's z_stream structure which provides convenient
    decompression functionality.
    """
    stream = rzlib.null_stream

    def __init__(self, space, wbits=rzlib.MAX_WBITS):
        """
        Initialize a new decompression object.

        wbits is an integer between 8 and MAX_WBITS or -8 and -MAX_WBITS
        (inclusive) giving the number of "window bits" to use for compression
        and decompression.  See the documentation for deflateInit2 and
        inflateInit2.
        """
        self.space = space
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
            self.stream = null_stream


    def decompress(self, data, max_length=0):
        """
        decompress(data[, max_length]) -- Return a string containing the
        decompressed version of the data.

        After calling this function, some of the input data may still be stored
        in internal buffers for later processing.

        Call the flush() method to clear these buffers.

        If the max_length parameter is specified then the return value will be
        no longer than max_length.  Unconsumed input data will be stored in the
        unconsumed_tail attribute.
        """
        if max_length != 0:      # XXX
            raise OperationError(self.space.w_NotImplementedError,
                                 self.space.wrap("max_length != 0"))
        try:
            result = rzlib.decompress(self.stream, data)
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        return self.space.wrap(result)
    decompress.unwrap_spec = ['self', str, int]


    def flush(self, length=0):
        """
        flush( [length] ) -- Return a string containing any remaining
        decompressed data. length, if given, is the initial size of the output
        buffer.

        The decompressor object can no longer be used after this call.
        """
        try:
            result = rzlib.decompress(self.stream, '', rzlib.Z_FINISH)
        except rzlib.RZlibError, e:
            raise zlib_error(self.space, e.msg)
        return self.space.wrap(result)
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
    __doc__ = """decompressobj([wbits]) -- Return a decompressor object.

Optional arg wbits is the window buffer size.
""")
