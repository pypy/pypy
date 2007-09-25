# import zlib

from pypy.interpreter.gateway import ObjSpace, W_Root, interp2app
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.error import OperationError

from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.rpython.tool import rffi_platform

includes = ['zlib.h']
libraries = ['z']

class SimpleCConfig:
    """
    Definitions for basic types defined by zlib.
    """
    _includes_ = includes

    # XXX If Z_PREFIX was defined for the libz build, then these types are
    # named z_uInt, z_uLong, and z_Bytef instead.
    uInt = rffi_platform.SimpleType('uInt', rffi.UINT)
    uLong = rffi_platform.SimpleType('uLong', rffi.ULONG)
    Bytef = rffi_platform.SimpleType('Bytef', rffi.UCHAR)
    voidpf = rffi_platform.SimpleType('voidpf', rffi.VOIDP)

    Z_OK = rffi_platform.ConstantInteger('Z_OK')
    Z_STREAM_ERROR = rffi_platform.ConstantInteger('Z_STREAM_ERROR')

    ZLIB_VERSION = rffi_platform.DefinedConstantString('ZLIB_VERSION')

    Z_DEFLATED = rffi_platform.ConstantInteger('Z_DEFLATED')
    Z_DEFAULT_STRATEGY = rffi_platform.ConstantInteger('Z_DEFAULT_STRATEGY')
    Z_DEFAULT_COMPRESSION = rffi_platform.ConstantInteger(
        'Z_DEFAULT_COMPRESSION')
    Z_NO_FLUSH = rffi_platform.ConstantInteger(
        'Z_NO_FLUSH')

config = rffi_platform.configure(SimpleCConfig)
voidpf = config['voidpf']
uInt = config['uInt']
uLong = config['uLong']
Bytef = config['Bytef']
Bytefp = lltype.Ptr(lltype.Array(Bytef, hints={'nolength': True}))

Z_OK = config['Z_OK']
Z_STREAM_ERROR = config['Z_STREAM_ERROR']

ZLIB_VERSION = config['ZLIB_VERSION']

Z_DEFAULT_COMPRESSION = config['Z_DEFAULT_COMPRESSION']
Z_DEFAULT_STRATEGY = config['Z_DEFAULT_STRATEGY']
Z_NO_FLUSH = config['Z_DEFAULT_COMPRESSION']
Z_DEFLATED = config['Z_DEFLATED']

class ComplexCConfig:
    """
    Definitions of structure types defined by zlib and based on SimpleCConfig
    definitions.
    """
    _includes_ = includes

    z_stream = rffi_platform.Struct(
        'z_stream',
        [('next_in', Bytefp),
         ('avail_in', uInt),
         ('total_in', uLong),

         ('next_out', Bytefp),
         ('avail_out', uInt),
         ('total_out', uLong),

         ('msg', rffi.CCHARP),

         ('zalloc', lltype.Ptr(
                    lltype.FuncType([voidpf, uInt, uInt], voidpf))),
         ('zfree', lltype.Ptr(
                    lltype.FuncType([voidpf, voidpf], lltype.Void))),

         ('opaque', voidpf),

         ('data_type', rffi.INT),
         ('adler', uLong),
         ('reserved', uLong)
         ])

config = rffi_platform.configure(ComplexCConfig)
z_stream = config['z_stream']
z_stream_p = lltype.Ptr(z_stream)

def zlib_external(*a, **kw):
    kw['includes'] = includes
    kw['libraries'] = libraries
    return rffi.llexternal(*a, **kw)

_crc32 = zlib_external('crc32', [uLong, Bytefp, uInt], uLong)
_adler32 = zlib_external('adler32', [uLong, Bytefp, uInt], uLong)


# XXX I want to call deflateInit2, not deflateInit2_
_deflateInit2_ = zlib_external(
    'deflateInit2_',
    [z_stream_p, # stream
     rffi.INT, # level
     rffi.INT, # method
     rffi.INT, # window bits
     rffi.INT, # mem level
     rffi.INT, # strategy
     rffi.CCHARP, # version
     rffi.INT], # stream size
    rffi.INT)
_deflate = zlib_external('deflate', [z_stream_p, rffi.INT], rffi.INT)

def _deflateInit2(stream, level, method, wbits, memlevel, strategy):
    version = rffi.str2charp(ZLIB_VERSION)
    size = llmemory.sizeof(z_stream)
    result = _deflateInit2_(
        stream, level, method, wbits, memlevel, strategy, version, size)
    rffi.free_charp(version)
    return result


def crc32(space, string, start=0):
    """
    crc32(string[, start]) -- Compute a CRC-32 checksum of string.

    An optional starting value can be specified.  The returned checksum is
    an integer.
    """
    bytes = rffi.str2charp(string)
    checksum = _crc32(start, rffi.cast(Bytefp, bytes), len(string))
    rffi.free_charp(bytes)

    # This is, perhaps, a little stupid.  zlib returns the checksum unsigned.
    # CPython exposes it as a signed value, though. -exarkun
    checksum = rffi.cast(rffi.INT, checksum)

    return space.wrap(checksum)
crc32.unwrap_spec = [ObjSpace, str, int]


def adler32(space, string, start=1):
    """
    adler32(string[, start]) -- Compute an Adler-32 checksum of string.

    An optional starting value can be specified.  The returned checksum is
    an integer.
    """
    bytes = rffi.str2charp(string)
    checksum = _adler32(start, rffi.cast(Bytefp, bytes), len(string))
    rffi.free_charp(bytes)

    # This is, perhaps, a little stupid.  zlib returns the checksum unsigned.
    # CPython exposes it as a signed value, though. -exarkun
    checksum = rffi.cast(rffi.INT, checksum)

    return space.wrap(checksum)
adler32.unwrap_spec = [ObjSpace, str, int]


class _StreamBase(Wrappable):
    """
    Base for classes which want to have a z_stream allocated when they are
    initialized and de-allocated when they are freed.
    """
    def __init__(self, space):
        self.space = space
        self.stream = lltype.malloc(z_stream, flavor='raw')
        self.stream.c_zalloc = lltype.nullptr(z_stream.c_zalloc.TO)
        self.stream.c_zfree = lltype.nullptr(z_stream.c_zfree.TO)
        self.stream.c_avail_in = rffi.cast(lltype.Unsigned, 0)
        self.stream.c_next_in = lltype.nullptr(z_stream.c_next_in.TO)


    def __del__(self):
        lltype.free(self.stream, flavor='raw')



def error_from_zlib(space, status):
    if status == Z_STREAM_ERROR:
        return OperationError(
            space.w_ValueError,
            space.wrap("Invalid initialization option"))
    assert False, "unhandled status %s" % (status,)


class Compress(_StreamBase):
    """
    Wrapper around zlib's z_stream structure which provides convenient
    compression functionality.
    """
    def __init__(self, space, w_level):
        # XXX CPython actually exposes 4 more undocumented parameters beyond
        # level.
        if space.is_w(w_level, space.w_None):
            level = Z_DEFAULT_COMPRESSION
        else:
            level = space.int_w(w_level)

        _StreamBase.__init__(self, space)

        method = Z_DEFLATED
        windowBits = 15
        memLevel = 8
        strategy = Z_DEFAULT_STRATEGY

        result = _deflateInit2(
            self.stream, level, method, windowBits, memLevel, strategy)

        if result != Z_OK:
            raise error_from_zlib(self.space, result)


    def compress(self, data, length=16384):
        """
        compress(data) -- Return a string containing data compressed.

        After calling this function, some of the input data may still be stored
        in internal buffers for later processing.

        Call the flush() method to clear these buffers.
        """
        self.stream.c_avail_in = rffi.cast(lltype.Unsigned, len(data))
        self.stream.c_next_in = lltype.malloc(
            Bytefp.TO, len(data), flavor='raw')
        for i in xrange(len(data)):
            self.stream.c_next_in[i] = rffi.cast(Bytef, data[i])
        self.stream.c_avail_out = rffi.cast(lltype.Unsigned, length)
        self.stream.c_next_out = lltype.malloc(
            Bytefp.TO, length, flavor='raw')
        result = _deflate(self.stream, Z_NO_FLUSH)
        if result != Z_OK:
            raise error_from_zlib(self.space, result)
        return rffi.charp2str(self.stream.c_next_out)
    compress.unwrap_spec = ['self', str, int]


    def flush(self, mode=0): # XXX =Z_FINISH
        """
        flush( [mode] ) -- Return a string containing any remaining compressed
        data.

        mode can be one of the constants Z_SYNC_FLUSH, Z_FULL_FLUSH, Z_FINISH;
        the default value used when mode is not specified is Z_FINISH.

        If mode == Z_FINISH, the compressor object can no longer be used after
        calling the flush() method.  Otherwise, more data can still be
        compressed.
        """
        return self.space.wrap('')
    flush.unwrap_spec = ['self', int]


def Compress___new__(space, w_subtype, w_level=None):
    """
    Create a new z_stream and call its initializer.
    """
    stream = space.allocate_instance(Compress, w_subtype)
    stream = space.interp_w(Compress, stream)
    Compress.__init__(stream, space, w_level)
    return space.wrap(stream)
Compress___new__.unwrap_spec = [ObjSpace, W_Root, W_Root]


Compress.typedef = TypeDef(
    'Compress',
    __new__ = interp2app(Compress___new__),
    compress = interp2app(Compress.compress),
    flush = interp2app(Compress.flush))



class Decompress(_StreamBase):
    """
    Wrapper around zlib's z_stream structure which provides convenient
    decompression functionality.
    """
    def __init__(self, space, wbits):
        """
        Initialize a new decompression object.

        wbits is an integer between 8 and MAX_WBITS or -8 and -MAX_WBITS
        (inclusive) giving the number of "window bits" to use for compression
        and decompression.  See the documentation for deflateInit2 and
        inflateInit2.
        """
        _StreamBase.__init__(self, space)
        self.wbits = wbits


    def decompress(self, data, max_length=0): # XXX =None
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
        return self.space.wrap('')
    decompress.unwrap_spec = ['self', str, int]


    def flush(self, length=0):
        """
        flush( [length] ) -- Return a string containing any remaining
        decompressed data. length, if given, is the initial size of the output
        buffer.

        The decompressor object can no longer be used after this call.
        """
        return self.space.wrap('')
    flush.unwrap_spec = ['self', int]


def Decompress___new__(space, w_subtype, w_anything=None):
    """
    Create a new Decompress and call its initializer.
    """
    stream = space.allocate_instance(Decompress, w_subtype)
    stream = space.interp_w(Decompress, stream)
    Decompress.__init__(stream, space, w_anything)
    return space.wrap(stream)
Decompress___new__.unwrap_spec = [ObjSpace, W_Root, W_Root]


Decompress.typedef = TypeDef(
    'Decompress',
    __new__ = interp2app(Decompress___new__),
    decompress = interp2app(Decompress.decompress),
    flush = interp2app(Decompress.flush))
