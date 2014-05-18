from __future__ import with_statement
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem import lltype
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import TypeDef, interp_attrproperty_bytes
from pypy.interpreter.typedef import GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator.platform import platform as compiler
from rpython.rlib.rarithmetic import intmask, r_longlong
import sys


if compiler.name == "msvc":
    libname = 'libbz2'
else:
    libname = 'bz2'
eci = ExternalCompilationInfo(
    includes = ['stdio.h', 'sys/types.h', 'bzlib.h'],
    libraries = [libname],
    )
eci = platform.configure_external_library(
    'bz2', eci,
    [dict(prefix='bzip2-')])
if not eci:
    raise ImportError("Could not find bzip2 library")

class CConfig:
    _compilation_info_ = eci
    calling_conv = 'c'

    CHECK_LIBRARY = platform.Has('dump("x", (long)&BZ2_bzCompress)')

    off_t = platform.SimpleType("off_t", rffi.LONGLONG)
    size_t = platform.SimpleType("size_t", rffi.ULONG)
    BUFSIZ = platform.ConstantInteger("BUFSIZ")
    _alloc_type = lltype.FuncType([rffi.VOIDP, rffi.INT, rffi.INT], rffi.VOIDP)
    _free_type = lltype.FuncType([rffi.VOIDP, rffi.VOIDP], lltype.Void)
    SEEK_SET = platform.ConstantInteger("SEEK_SET")
    bz_stream = platform.Struct('bz_stream',
                                [('next_in', rffi.CCHARP),
                                 ('avail_in', rffi.UINT),
                                 ('total_in_lo32', rffi.UINT),
                                 ('total_in_hi32', rffi.UINT),
                                 ('next_out', rffi.CCHARP),
                                 ('avail_out', rffi.UINT),
                                 ('total_out_lo32', rffi.UINT),
                                 ('total_out_hi32', rffi.UINT),
                                 ('state', rffi.VOIDP),
                                 ('bzalloc', lltype.Ptr(_alloc_type)),
                                 ('bzfree', lltype.Ptr(_free_type)),
                                 ('opaque', rffi.VOIDP),
                                 ])

FILE = rffi.COpaquePtr('FILE')
BZFILE = rffi.COpaquePtr('BZFILE')


constants = {}
constant_names = ['BZ_RUN', 'BZ_FLUSH', 'BZ_FINISH', 'BZ_OK',
    'BZ_RUN_OK', 'BZ_FLUSH_OK', 'BZ_FINISH_OK', 'BZ_STREAM_END',
    'BZ_SEQUENCE_ERROR', 'BZ_PARAM_ERROR', 'BZ_MEM_ERROR', 'BZ_DATA_ERROR',
    'BZ_DATA_ERROR_MAGIC', 'BZ_IO_ERROR', 'BZ_UNEXPECTED_EOF',
    'BZ_OUTBUFF_FULL', 'BZ_CONFIG_ERROR']
for name in constant_names:
    setattr(CConfig, name, platform.DefinedConstantInteger(name))

class cConfig(object):
    pass
for k, v in platform.configure(CConfig).items():
    setattr(cConfig, k, v)
if not cConfig.CHECK_LIBRARY:
    raise ImportError("Invalid bz2 library")

for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value
locals().update(constants)

off_t = cConfig.off_t
bz_stream = lltype.Ptr(cConfig.bz_stream)
BUFSIZ = cConfig.BUFSIZ
SEEK_SET = cConfig.SEEK_SET
BZ_OK = cConfig.BZ_OK
BZ_STREAM_END = cConfig.BZ_STREAM_END
BZ_CONFIG_ERROR = cConfig.BZ_CONFIG_ERROR
BZ_PARAM_ERROR = cConfig.BZ_PARAM_ERROR
BZ_DATA_ERROR = cConfig.BZ_DATA_ERROR
BZ_DATA_ERROR_MAGIC = cConfig.BZ_DATA_ERROR_MAGIC
BZ_IO_ERROR = cConfig.BZ_IO_ERROR
BZ_MEM_ERROR = cConfig.BZ_MEM_ERROR
BZ_UNEXPECTED_EOF = cConfig.BZ_UNEXPECTED_EOF
BZ_SEQUENCE_ERROR = cConfig.BZ_SEQUENCE_ERROR

if BUFSIZ < 8192:
    SMALLCHUNK = 8192
else:
    SMALLCHUNK = BUFSIZ

if rffi.sizeof(rffi.INT) > 4:
    BIGCHUNK = 512 * 32
else:
    BIGCHUNK = 512 * 1024

if BZ_CONFIG_ERROR:
    if rffi.sizeof(rffi.LONG) >= 8:
        def _bzs_total_out(bzs):
            return (rffi.getintfield(bzs, 'c_total_out_hi32') << 32) + \
                   rffi.getintfield(bzs, 'c_total_out_lo32')
    else:
        # we can't return a long long value from here, because most
        # callers wouldn't be able to handle it anyway
        def _bzs_total_out(bzs):
            if rffi.getintfield(bzs, 'c_total_out_hi32') != 0 or \
                   rffi.getintfield(bzs, 'c_total_out_lo32') > sys.maxint:
                raise MemoryError
            return rffi.getintfield(bzs, 'c_total_out_lo32')
else:
    XXX    # this case needs fixing (old bz2 library?)
    def _bzs_total_out(bzs):
        return bzs.total_out

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=
                           CConfig._compilation_info_, **kwds)

# the least but one parameter should be rffi.VOIDP but it's not used
# so I trick the compiler to not complain about constanst pointer passed
# to void* arg
BZ2_bzReadOpen = external('BZ2_bzReadOpen', [rffi.INTP, FILE, rffi.INT,
    rffi.INT, rffi.INTP, rffi.INT], BZFILE)
BZ2_bzWriteOpen = external('BZ2_bzWriteOpen', [rffi.INTP, FILE, rffi.INT,
    rffi.INT, rffi.INT], BZFILE)
BZ2_bzReadClose = external('BZ2_bzReadClose', [rffi.INTP, BZFILE], lltype.Void)
BZ2_bzWriteClose = external('BZ2_bzWriteClose', [rffi.INTP, BZFILE,
    rffi.INT, rffi.UINTP, rffi.UINTP], lltype.Void)
BZ2_bzRead = external('BZ2_bzRead', [rffi.INTP, BZFILE, rffi.CCHARP, rffi.INT],
                      rffi.INT)
BZ2_bzWrite = external('BZ2_bzWrite', [rffi.INTP, BZFILE, rffi.CCHARP,
                                       rffi.INT], lltype.Void)
BZ2_bzCompressInit = external('BZ2_bzCompressInit', [bz_stream, rffi.INT,
                              rffi.INT, rffi.INT], rffi.INT)
BZ2_bzCompressEnd = external('BZ2_bzCompressEnd', [bz_stream], rffi.INT,
                             releasegil=False)
BZ2_bzCompress = external('BZ2_bzCompress', [bz_stream, rffi.INT], rffi.INT)
BZ2_bzDecompressInit = external('BZ2_bzDecompressInit', [bz_stream, rffi.INT,
                                                         rffi.INT], rffi.INT)
BZ2_bzDecompressEnd = external('BZ2_bzDecompressEnd', [bz_stream], rffi.INT,
                               releasegil=False)
BZ2_bzDecompress = external('BZ2_bzDecompress', [bz_stream], rffi.INT)

def _catch_bz2_error(space, bzerror):
    if BZ_CONFIG_ERROR and bzerror == BZ_CONFIG_ERROR:
        raise OperationError(space.w_SystemError,
            space.wrap("the bz2 library was not compiled correctly"))
    if bzerror == BZ_PARAM_ERROR:
        raise OperationError(space.w_SystemError,
            space.wrap("the bz2 library has received wrong parameters"))
    elif bzerror == BZ_MEM_ERROR:
        raise OperationError(space.w_MemoryError, space.wrap(""))
    elif bzerror in (BZ_DATA_ERROR, BZ_DATA_ERROR_MAGIC):
        raise OperationError(space.w_IOError, space.wrap("invalid data stream"))
    elif bzerror == BZ_IO_ERROR:
        raise OperationError(space.w_IOError, space.wrap("unknown IO error"))
    elif bzerror == BZ_UNEXPECTED_EOF:
        raise OperationError(space.w_EOFError,
            space.wrap(
                "compressed file ended before the logical end-of-stream was detected"))
    elif bzerror == BZ_SEQUENCE_ERROR:
        raise OperationError(space.w_RuntimeError,
            space.wrap("wrong sequence of bz2 library commands used"))

def _new_buffer_size(current_size):
    # keep doubling until we reach BIGCHUNK; then the buffer size is no
    # longer increased
    if current_size < BIGCHUNK:
        return current_size + current_size
    return current_size

# ____________________________________________________________

class OutBuffer(object):
    """Handler for the output buffer.  A bit custom code trying to
    encapsulate the logic of setting up the fields of 'bzs' and
    allocating raw memory as needed.
    """
    def __init__(self, bzs, initial_size=SMALLCHUNK):
        # when the constructor is called, allocate a piece of memory
        # of length 'piece_size' and make bzs ready to dump there.
        self.temp = []
        self.bzs = bzs
        self._allocate_chunk(initial_size)

    def _allocate_chunk(self, size):
        self.raw_buf, self.gc_buf = rffi.alloc_buffer(size)
        self.current_size = size
        self.bzs.c_next_out = self.raw_buf
        rffi.setintfield(self.bzs, 'c_avail_out', size)

    def _get_chunk(self, chunksize):
        assert 0 <= chunksize <= self.current_size
        raw_buf = self.raw_buf
        gc_buf = self.gc_buf
        s = rffi.str_from_buffer(raw_buf, gc_buf, self.current_size, chunksize)
        rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
        self.current_size = 0
        return s

    def prepare_next_chunk(self):
        size = self.current_size
        self.temp.append(self._get_chunk(size))
        self._allocate_chunk(_new_buffer_size(size))

    def make_result_string(self):
        count_unoccupied = rffi.getintfield(self.bzs, 'c_avail_out')
        s = self._get_chunk(self.current_size - count_unoccupied)
        if self.temp:
            self.temp.append(s)
            return ''.join(self.temp)
        else:
            return s

    def free(self):
        if self.current_size > 0:
            rffi.keep_buffer_alive_until_here(self.raw_buf, self.gc_buf)

    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.free()


@unwrap_spec(compresslevel=int)
def descr_compressor__new__(space, w_subtype, compresslevel=9):
    x = space.allocate_instance(W_BZ2Compressor, w_subtype)
    x = space.interp_w(W_BZ2Compressor, x)
    W_BZ2Compressor.__init__(x, space, compresslevel)
    return space.wrap(x)

class W_BZ2Compressor(W_Root):
    """BZ2Compressor([compresslevel=9]) -> compressor object

    Create a new compressor object. This object may be used to compress
    data sequentially. If you want to compress data in one shot, use the
    compress() function instead. The compresslevel parameter, if given,
    must be a number between 1 and 9."""
    def __init__(self, space, compresslevel):
        self.space = space
        self.bzs = lltype.malloc(bz_stream.TO, flavor='raw', zero=True)
        self.running = False
        self._init_bz2comp(compresslevel)

    def _init_bz2comp(self, compresslevel):
        if compresslevel < 1 or compresslevel > 9:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("compresslevel must be between 1 and 9"))

        bzerror = intmask(BZ2_bzCompressInit(self.bzs, compresslevel, 0, 0))
        if bzerror != BZ_OK:
            _catch_bz2_error(self.space, bzerror)

        self.running = True

    def __del__(self):
        BZ2_bzCompressEnd(self.bzs)
        lltype.free(self.bzs, flavor='raw')

    @unwrap_spec(data='bufferstr')
    def compress(self, data):
        """compress(data) -> string

        Provide more data to the compressor object. It will return chunks of
        compressed data whenever possible. When you've finished providing data
        to compress, call the flush() method to finish the compression process,
        and return what is left in the internal buffers."""

        datasize = len(data)

        if datasize == 0:
            return self.space.wrapbytes("")

        if not self.running:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("this object was already flushed"))

        in_bufsize = datasize

        with OutBuffer(self.bzs) as out:
            with lltype.scoped_alloc(rffi.CCHARP.TO, in_bufsize) as in_buf:

                for i in range(datasize):
                    in_buf[i] = data[i]

                self.bzs.c_next_in = in_buf
                rffi.setintfield(self.bzs, 'c_avail_in', in_bufsize)

                while True:
                    bzerror = BZ2_bzCompress(self.bzs, BZ_RUN)
                    if bzerror != BZ_RUN_OK:
                        _catch_bz2_error(self.space, bzerror)

                    if rffi.getintfield(self.bzs, 'c_avail_in') == 0:
                        break
                    elif rffi.getintfield(self.bzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                res = out.make_result_string()
                return self.space.wrapbytes(res)

    def flush(self):
        if not self.running:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("this object was already flushed"))
        self.running = False

        with OutBuffer(self.bzs) as out:
            while True:
                bzerror = BZ2_bzCompress(self.bzs, BZ_FINISH)
                if bzerror == BZ_STREAM_END:
                    break
                elif bzerror != BZ_FINISH_OK:
                    _catch_bz2_error(self.space, bzerror)

                if rffi.getintfield(self.bzs, 'c_avail_out') == 0:
                    out.prepare_next_chunk()

            res = out.make_result_string()
            return self.space.wrapbytes(res)

W_BZ2Compressor.typedef = TypeDef("BZ2Compressor",
    __doc__ = W_BZ2Compressor.__doc__,
    __new__ = interp2app(descr_compressor__new__),
    compress = interp2app(W_BZ2Compressor.compress),
    flush = interp2app(W_BZ2Compressor.flush),
)


def descr_decompressor__new__(space, w_subtype):
    x = space.allocate_instance(W_BZ2Decompressor, w_subtype)
    x = space.interp_w(W_BZ2Decompressor, x)
    W_BZ2Decompressor.__init__(x, space)
    return space.wrap(x)


class W_BZ2Decompressor(W_Root):
    """BZ2Decompressor() -> decompressor object

    Create a new decompressor object. This object may be used to decompress
    data sequentially. If you want to decompress data in one shot, use the
    decompress() function instead."""

    def __init__(self, space):
        self.space = space

        self.bzs = lltype.malloc(bz_stream.TO, flavor='raw', zero=True)
        self.running = False
        self.unused_data = ""

        self._init_bz2decomp()

    def _init_bz2decomp(self):
        bzerror = BZ2_bzDecompressInit(self.bzs, 0, 0)
        if bzerror != BZ_OK:
            _catch_bz2_error(self.space, bzerror)

        self.running = True

    def __del__(self):
        BZ2_bzDecompressEnd(self.bzs)
        lltype.free(self.bzs, flavor='raw')

    def eof_w(self, space):
        if self.running:
            return space.w_False
        else:
            return space.w_True

    @unwrap_spec(data='bufferstr')
    def decompress(self, data):
        """decompress(data) -> string

        Provide more data to the decompressor object. It will return chunks
        of decompressed data whenever possible. If you try to decompress data
        after the end of stream is found, EOFError will be raised. If any data
        was found after the end of stream, it'll be ignored and saved in
        unused_data attribute."""

        if not self.running:
            raise OperationError(self.space.w_EOFError,
                self.space.wrap("end of stream was already found"))
        if data == '':
            return self.space.wrapbytes('')

        in_bufsize = len(data)

        with lltype.scoped_alloc(rffi.CCHARP.TO, in_bufsize) as in_buf:
            for i in range(in_bufsize):
                in_buf[i] = data[i]
            self.bzs.c_next_in = in_buf
            rffi.setintfield(self.bzs, 'c_avail_in', in_bufsize)

            with OutBuffer(self.bzs) as out:
                while True:
                    bzerror = BZ2_bzDecompress(self.bzs)
                    if bzerror == BZ_STREAM_END:
                        if rffi.getintfield(self.bzs, 'c_avail_in') != 0:
                            unused = [self.bzs.c_next_in[i]
                                      for i in range(
                                          rffi.getintfield(self.bzs,
                                                           'c_avail_in'))]
                            self.unused_data = "".join(unused)
                        self.running = False
                        break
                    if bzerror != BZ_OK:
                        _catch_bz2_error(self.space, bzerror)

                    if rffi.getintfield(self.bzs, 'c_avail_in') == 0:
                        break
                    elif rffi.getintfield(self.bzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                res = out.make_result_string()
                return self.space.wrapbytes(res)


W_BZ2Decompressor.typedef = TypeDef("BZ2Decompressor",
    __doc__ = W_BZ2Decompressor.__doc__,
    __new__ = interp2app(descr_decompressor__new__),
    unused_data = interp_attrproperty_bytes("unused_data", W_BZ2Decompressor),
    eof = GetSetProperty(W_BZ2Decompressor.eof_w),
    decompress = interp2app(W_BZ2Decompressor.decompress),
)


@unwrap_spec(data='bufferstr', compresslevel=int)
def compress(space, data, compresslevel=9):
    """compress(data [, compresslevel=9]) -> string

    Compress data in one shot. If you want to compress data sequentially,
    use an instance of BZ2Compressor instead. The compresslevel parameter, if
    given, must be a number between 1 and 9."""

    if compresslevel < 1 or compresslevel > 9:
        raise OperationError(space.w_ValueError,
            space.wrap("compresslevel must be between 1 and 9"))

    with lltype.scoped_alloc(bz_stream.TO, zero=True) as bzs:
        in_bufsize = len(data)

        with lltype.scoped_alloc(rffi.CCHARP.TO, in_bufsize) as in_buf:
            for i in range(in_bufsize):
                in_buf[i] = data[i]
            bzs.c_next_in = in_buf
            rffi.setintfield(bzs, 'c_avail_in', in_bufsize)

            # conforming to bz2 manual, this is large enough to fit compressed
            # data in one shot. We will check it later anyway.
            with OutBuffer(bzs,
                           in_bufsize + (in_bufsize / 100 + 1) + 600) as out:

                bzerror = BZ2_bzCompressInit(bzs, compresslevel, 0, 0)
                if bzerror != BZ_OK:
                    _catch_bz2_error(space, bzerror)

                while True:
                    bzerror = BZ2_bzCompress(bzs, BZ_FINISH)
                    if bzerror == BZ_STREAM_END:
                        break
                    elif bzerror != BZ_FINISH_OK:
                        BZ2_bzCompressEnd(bzs)
                        _catch_bz2_error(space, bzerror)

                    if rffi.getintfield(bzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                res = out.make_result_string()
                BZ2_bzCompressEnd(bzs)
                return space.wrapbytes(res)

@unwrap_spec(data='bufferstr')
def decompress(space, data):
    """decompress(data) -> decompressed data

    Decompress data in one shot. If you want to decompress data sequentially,
    use an instance of BZ2Decompressor instead."""

    in_bufsize = len(data)
    if in_bufsize == 0:
        return space.wrapbytes("")

    with lltype.scoped_alloc(bz_stream.TO, zero=True) as bzs:
        with lltype.scoped_alloc(rffi.CCHARP.TO, in_bufsize) as in_buf:
            for i in range(in_bufsize):
                in_buf[i] = data[i]
            bzs.c_next_in = in_buf
            rffi.setintfield(bzs, 'c_avail_in', in_bufsize)

            with OutBuffer(bzs) as out:
                bzerror = BZ2_bzDecompressInit(bzs, 0, 0)
                if bzerror != BZ_OK:
                    _catch_bz2_error(space, bzerror)

                while True:
                    bzerror = BZ2_bzDecompress(bzs)
                    if bzerror == BZ_STREAM_END:
                        break
                    if bzerror != BZ_OK:
                        BZ2_bzDecompressEnd(bzs)
                    _catch_bz2_error(space, bzerror)

                    if rffi.getintfield(bzs, 'c_avail_in') == 0:
                        BZ2_bzDecompressEnd(bzs)
                        raise OperationError(space.w_ValueError, space.wrap(
                            "couldn't find end of stream"))
                    elif rffi.getintfield(bzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                res = out.make_result_string()
                BZ2_bzDecompressEnd(bzs)
                return space.wrapbytes(res)
