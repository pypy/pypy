import sys

from pypy.rlib.rstring import StringBuilder
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.translator.platform import platform as compiler, CompilationError
from pypy.translator.tool.cbuild import ExternalCompilationInfo


if compiler.name == "msvc":
    libname = 'zlib'
else:
    libname = 'z'
eci = ExternalCompilationInfo(
        libraries=[libname],
        includes=['zlib.h']
    )
try:
    eci = rffi_platform.configure_external_library(
        libname, eci,
        [dict(prefix='zlib-'),
         ])
except CompilationError:
    raise ImportError("Could not find a zlib library")


constantnames = '''
    Z_OK  Z_STREAM_ERROR  Z_BUF_ERROR  Z_MEM_ERROR  Z_STREAM_END Z_DATA_ERROR
    Z_DEFLATED  Z_DEFAULT_STRATEGY  Z_DEFAULT_COMPRESSION
    Z_NO_FLUSH  Z_FINISH  Z_SYNC_FLUSH  Z_FULL_FLUSH
    MAX_WBITS  MAX_MEM_LEVEL
    Z_BEST_SPEED  Z_BEST_COMPRESSION  Z_DEFAULT_COMPRESSION
    Z_FILTERED  Z_HUFFMAN_ONLY  Z_DEFAULT_STRATEGY
    '''.split()

class SimpleCConfig:
    """
    Definitions for basic types defined by zlib.
    """
    _compilation_info_ = eci

    # XXX If Z_PREFIX was defined for the libz build, then these types are
    # named z_uInt, z_uLong, and z_Bytef instead.
    uInt = rffi_platform.SimpleType('uInt', rffi.UINT)
    uLong = rffi_platform.SimpleType('uLong', rffi.ULONG)
    Bytef = rffi_platform.SimpleType('Bytef', rffi.UCHAR)
    voidpf = rffi_platform.SimpleType('voidpf', rffi.VOIDP)

    ZLIB_VERSION = rffi_platform.DefinedConstantString('ZLIB_VERSION')

for _name in constantnames:
    setattr(SimpleCConfig, _name, rffi_platform.ConstantInteger(_name))

config = rffi_platform.configure(SimpleCConfig)
voidpf = config['voidpf']
uInt = config['uInt']
uLong = config['uLong']
Bytef = config['Bytef']
Bytefp = lltype.Ptr(lltype.Array(Bytef, hints={'nolength': True}))

ZLIB_VERSION = config['ZLIB_VERSION']

for _name in constantnames:
    globals()[_name] = config[_name]

# The following parameter is copied from zutil.h, version 0.95,
# according to CPython's zlibmodule.c
DEFLATED = Z_DEFLATED
if MAX_MEM_LEVEL >= 8:
    DEF_MEM_LEVEL = 8
else:
    DEF_MEM_LEVEL = MAX_MEM_LEVEL

OUTPUT_BUFFER_SIZE = 32*1024


class ComplexCConfig:
    """
    Definitions of structure types defined by zlib and based on SimpleCConfig
    definitions.
    """
    _compilation_info_ = eci

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
    kw['compilation_info'] = eci
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

_deflateEnd = zlib_external('deflateEnd', [z_stream_p], rffi.INT)

def _deflateInit2(stream, level, method, wbits, memlevel, strategy):
    size = rffi.sizeof(z_stream)
    result = _deflateInit2_(
        stream, level, method, wbits, memlevel, strategy, ZLIB_VERSION, size)
    return result

# XXX I also want to call inflateInit2 instead of inflateInit2_
_inflateInit2_ = zlib_external(
    'inflateInit2_',
    [z_stream_p, # stream
     rffi.INT, # window bits
     rffi.CCHARP, # version
     rffi.INT], # stream size
    rffi.INT)
_inflate = zlib_external('inflate', [z_stream_p, rffi.INT], rffi.INT)

_inflateEnd = zlib_external('inflateEnd', [z_stream_p], rffi.INT)

def _inflateInit2(stream, wbits):
    size = rffi.sizeof(z_stream)
    result = _inflateInit2_(stream, wbits, ZLIB_VERSION, size)
    return result

# ____________________________________________________________

CRC32_DEFAULT_START = 0

def crc32(string, start=CRC32_DEFAULT_START):
    """
    Compute the CRC32 checksum of the string, possibly with the given
    start value, and return it as a unsigned 32 bit integer.
    """
    bytes = rffi.get_nonmovingbuffer(string)
    try:
        checksum = _crc32(start, rffi.cast(Bytefp, bytes), len(string))
    finally:
        rffi.free_nonmovingbuffer(string, bytes)
    return checksum


ADLER32_DEFAULT_START = 1

def adler32(string, start=ADLER32_DEFAULT_START):
    """
    Compute the Adler-32 checksum of the string, possibly with the given
    start value, and return it as a unsigned 32 bit integer.
    """
    bytes = rffi.get_nonmovingbuffer(string)
    try:
        checksum = _adler32(start, rffi.cast(Bytefp, bytes), len(string))
    finally:
        rffi.free_nonmovingbuffer(string, bytes)
    return checksum

# ____________________________________________________________

class RZlibError(Exception):
    """Exception raised by failing operations in pypy.rlib.rzlib."""
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

    def fromstream(stream, err, while_doing):
        """Return a RZlibError with a message formatted from a zlib error
        code and stream.
        """
        if stream.c_msg:
            reason = rffi.charp2str(stream.c_msg)
        elif err == Z_MEM_ERROR:
            reason = "out of memory"
        elif err == Z_BUF_ERROR:
            reason = "incomplete or truncated stream"
        elif err == Z_STREAM_ERROR:
            reason = "inconsistent stream state"
        elif err == Z_DATA_ERROR:
            reason = "invalid input data"
        else:
            reason = ""

        if reason:
            delim = ": "
        else:
            delim = ""
        msg = "Error %d %s%s%s" % (err, while_doing, delim, reason)
        return RZlibError(msg)
    fromstream = staticmethod(fromstream)

null_stream = lltype.nullptr(z_stream)


def deflateInit(level=Z_DEFAULT_COMPRESSION, method=Z_DEFLATED,
                wbits=MAX_WBITS, memLevel=DEF_MEM_LEVEL,
                strategy=Z_DEFAULT_STRATEGY):
    """
    Allocate and return an opaque 'stream' object that can be used to
    compress data.
    """
    stream = lltype.malloc(z_stream, flavor='raw', zero=True)
    err = _deflateInit2(stream, level, method, wbits, memLevel, strategy)
    if err == Z_OK:
        return stream
    else:
        try:
            if err == Z_STREAM_ERROR:
                raise ValueError("Invalid initialization option")
            else:
                raise RZlibError.fromstream(stream, err,
                    "while creating compression object")
        finally:
            lltype.free(stream, flavor='raw')


def deflateEnd(stream):
    """
    Free the resources associated with the deflate stream.
    """
    _deflateEnd(stream)
    lltype.free(stream, flavor='raw')


def inflateInit(wbits=MAX_WBITS):
    """
    Allocate and return an opaque 'stream' object that can be used to
    decompress data.
    """
    stream = lltype.malloc(z_stream, flavor='raw', zero=True)
    err = _inflateInit2(stream, wbits)
    if err == Z_OK:
        return stream
    else:
        try:
            if err == Z_STREAM_ERROR:
                raise ValueError("Invalid initialization option")
            else:
                raise RZlibError.fromstream(stream, err,
                    "while creating decompression object")
        finally:
            lltype.free(stream, flavor='raw')


def inflateEnd(stream):
    """
    Free the resources associated with the inflate stream.
    Note that this may raise RZlibError.
    """
    _inflateEnd(stream)
    lltype.free(stream, flavor='raw')


def compress(stream, data, flush=Z_NO_FLUSH):
    """
    Feed more data into a deflate stream.  Returns a string containing
    (a part of) the compressed data.  If flush != Z_NO_FLUSH, this also
    flushes the output data; see zlib.h or the documentation of the
    zlib module for the possible values of 'flush'.
    """
    # Warning, reentrant calls to the zlib with a given stream can cause it
    # to crash.  The caller of pypy.rlib.rzlib should use locks if needed.
    data, _, avail_in = _operate(stream, data, flush, sys.maxint, _deflate,
                                 "while compressing")
    assert not avail_in, "not all input consumed by deflate"
    return data


def decompress(stream, data, flush=Z_SYNC_FLUSH, max_length=sys.maxint):
    """
    Feed more data into an inflate stream.  Returns a tuple (string,
    finished, unused_data_length).  The string contains (a part of) the
    decompressed data.  If flush != Z_NO_FLUSH, this also flushes the
    output data; see zlib.h or the documentation of the zlib module for
    the possible values of 'flush'.

    The 'string' is never longer than 'max_length'.  The
    'unused_data_length' is the number of unprocessed input characters,
    either because they are after the end of the compressed stream or
    because processing it would cause the 'max_length' to be exceeded.
    """
    # Warning, reentrant calls to the zlib with a given stream can cause it
    # to crash.  The caller of pypy.rlib.rzlib should use locks if needed.

    # _operate() does not support the Z_FINISH method of decompressing.
    # We can use Z_SYNC_FLUSH instead and manually check that we got to
    # the end of the data.
    if flush == Z_FINISH:
        flush = Z_SYNC_FLUSH
        should_finish = True
    else:
        should_finish = False
    while_doing = "while decompressing data"
    data, err, avail_in = _operate(stream, data, flush, max_length, _inflate,
                                   while_doing)
    if should_finish:
        # detect incomplete input
        rffi.setintfield(stream, 'c_avail_in', 0)
        err = _inflate(stream, Z_FINISH)
        if err < 0:
            raise RZlibError.fromstream(stream, err, while_doing)
    finished = (err == Z_STREAM_END)
    return data, finished, avail_in


def _operate(stream, data, flush, max_length, cfunc, while_doing):
    """Common code for compress() and decompress().
    """
    # Prepare the input buffer for the stream
    inbuf = lltype.malloc(rffi.CCHARP.TO, len(data), flavor='raw')
    try:
        for i in xrange(len(data)):
            inbuf[i] = data[i]
        stream.c_next_in = rffi.cast(Bytefp, inbuf)
        rffi.setintfield(stream, 'c_avail_in', len(data))

        # Prepare the output buffer
        outbuf = lltype.malloc(rffi.CCHARP.TO, OUTPUT_BUFFER_SIZE,
                               flavor='raw')
        try:
            # Strategy: we call deflate() to get as much output data as
            # fits in the buffer, then accumulate all output into a list
            # of characters 'result'.  We don't need to gradually
            # increase the output buffer size because there is no
            # quadratic factor.
            result = StringBuilder()

            while True:
                stream.c_next_out = rffi.cast(Bytefp, outbuf)
                bufsize = OUTPUT_BUFFER_SIZE
                if max_length < bufsize:
                    if max_length <= 0:
                        err = Z_OK
                        break
                    bufsize = max_length
                max_length -= bufsize
                rffi.setintfield(stream, 'c_avail_out', bufsize)
                err = cfunc(stream, flush)
                if err == Z_OK or err == Z_STREAM_END:
                    # accumulate data into 'result'
                    avail_out = rffi.cast(lltype.Signed, stream.c_avail_out)
                    result.append_charpsize(outbuf, bufsize - avail_out)
                    # if the output buffer is full, there might be more data
                    # so we need to try again.  Otherwise, we're done.
                    if avail_out > 0:
                        break
                    # We're also done if we got a Z_STREAM_END (which should
                    # only occur when flush == Z_FINISH).
                    if err == Z_STREAM_END:
                        break
                    else:
                        continue
                elif err == Z_BUF_ERROR:
                    avail_out = rffi.cast(lltype.Signed, stream.c_avail_out)
                    # When compressing, we will only get Z_BUF_ERROR if
                    # the output buffer was full but there wasn't more
                    # output when we tried again, so it is not an error
                    # condition.
                    if avail_out == bufsize:
                        break

                # fallback case: report this error
                raise RZlibError.fromstream(stream, err, while_doing)

        finally:
            lltype.free(outbuf, flavor='raw')
    finally:
        lltype.free(inbuf, flavor='raw')

    # When decompressing, if the compressed stream of data was truncated,
    # then the zlib simply returns Z_OK and waits for more.  If it is
    # complete it returns Z_STREAM_END.
    return (result.build(),
            err,
            rffi.cast(lltype.Signed, stream.c_avail_in))
