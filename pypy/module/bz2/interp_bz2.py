from pypy.rpython.rctypes.tool import ctypes_platform
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.typedef import interp_attrproperty
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, interp2app
from pypy.rlib.streamio import Stream
from ctypes import *
import ctypes.util
import sys

from bzlib import bz_stream, BZFILE, FILE

libbz2 = cdll.LoadLibrary(ctypes.util.find_library("bz2"))

c_void = None

class CConfig:
    _header_ = """
    #include <stdio.h>
    #include <sys/types.h>
    #include <bzlib.h>
    """
    # XXX: with this it should compile fine but on my machine pypy doesn't
    # inject this header so it's pretty useless. Kept as a remind.
    # _includes_ = ["bzlib.h"]
    off_t = ctypes_platform.SimpleType("off_t", c_longlong)
    size_t = ctypes_platform.SimpleType("size_t", c_ulong)
    BUFSIZ = ctypes_platform.ConstantInteger("BUFSIZ")
    SEEK_SET = ctypes_platform.ConstantInteger("SEEK_SET")

constants = {}
constant_names = ['BZ_RUN', 'BZ_FLUSH', 'BZ_FINISH', 'BZ_OK',
    'BZ_RUN_OK', 'BZ_FLUSH_OK', 'BZ_FINISH_OK', 'BZ_STREAM_END',
    'BZ_SEQUENCE_ERROR', 'BZ_PARAM_ERROR', 'BZ_MEM_ERROR', 'BZ_DATA_ERROR',
    'BZ_DATA_ERROR_MAGIC', 'BZ_IO_ERROR', 'BZ_UNEXPECTED_EOF',
    'BZ_OUTBUFF_FULL', 'BZ_CONFIG_ERROR']
for name in constant_names:
    setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))
    
class cConfig:
    pass
cConfig.__dict__.update(ctypes_platform.configure(CConfig))

for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value
locals().update(constants)

off_t = cConfig.off_t
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
    
if sizeof(c_int) > 4:
    BIGCHUNK = 512 * 32
else:
    BIGCHUNK = 512 * 1024
    
MAXINT = sys.maxint

if BZ_CONFIG_ERROR:
    if sizeof(c_long) >= 8 or sizeof(c_longlong) >= 8:
        def _bzs_total_out(bzs):
            return (bzs.total_out_hi32 << 32) + bzs.total_out_lo32
    else:
        def _bzs_total_out(bzs):
            return bzs.total_out_lo32
else:
    def _bzs_total_out(bzs):
        return bzs.total_out

# the least but one parameter should be c_void_p but it's not used
# so I trick the compiler to not complain about constanst pointer passed
# to void* arg
libbz2.BZ2_bzReadOpen.argtypes = [POINTER(c_int), POINTER(FILE), c_int,
    c_int, POINTER(c_int), c_int]
libbz2.BZ2_bzReadOpen.restype = POINTER(BZFILE)
libbz2.BZ2_bzWriteOpen.argtypes = [POINTER(c_int), POINTER(FILE), c_int,
    c_int, c_int]
libbz2.BZ2_bzWriteOpen.restype = POINTER(BZFILE)
libbz2.BZ2_bzReadClose.argtypes = [POINTER(c_int), POINTER(BZFILE)]
libbz2.BZ2_bzReadClose.restype = c_void
libbz2.BZ2_bzWriteClose.argtypes = [POINTER(c_int), POINTER(BZFILE),
    c_int, POINTER(c_uint), POINTER(c_uint)]
libbz2.BZ2_bzWriteClose.restype = c_void
libbz2.BZ2_bzRead.argtypes = [POINTER(c_int), POINTER(BZFILE), POINTER(c_char), c_int]
libbz2.BZ2_bzRead.restype = c_int
libbz2.BZ2_bzWrite.argtypes = [POINTER(c_int), POINTER(BZFILE), c_char_p, c_int]
libbz2.BZ2_bzWrite.restype = c_void

libbz2.BZ2_bzCompressInit.argtypes = [POINTER(bz_stream), c_int, c_int, c_int]
libbz2.BZ2_bzCompressInit.restype = c_int
libbz2.BZ2_bzCompressEnd.argtypes = [POINTER(bz_stream)]
libbz2.BZ2_bzCompressEnd.restype = c_int
libbz2.BZ2_bzCompress.argtypes = [POINTER(bz_stream), c_int]
libbz2.BZ2_bzCompress.restype = c_int

libbz2.BZ2_bzDecompressInit.argtypes = [POINTER(bz_stream), c_int, c_int]
libbz2.BZ2_bzDecompressInit.restype = c_int
libbz2.BZ2_bzDecompressEnd.argtypes = [POINTER(bz_stream)]
libbz2.BZ2_bzDecompressEnd.restype = c_int
libbz2.BZ2_bzDecompress.argtypes = [POINTER(bz_stream)]
libbz2.BZ2_bzDecompress.restype = c_int

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
    if current_size > SMALLCHUNK:
        # keep doubling until we reach BIGCHUNK
        # then keep adding BIGCHUNK
        if current_size <= BIGCHUNK:
            return current_size + current_size
        else:
            return current_size + BIGCHUNK
    return current_size + SMALLCHUNK

def open_file_as_stream(space, path, mode="r", buffering=-1, compresslevel=9):
    from pypy.rlib.streamio import decode_mode, open_path_helper
    from pypy.rlib.streamio import construct_stream_tower
    from pypy.module._file.interp_file import wrap_oserror_as_ioerror, W_Stream
    from pypy.module._file.interp_file import is_mode_ok
    is_mode_ok(space, mode)
    os_flags, universal, reading, writing, basemode = decode_mode(mode)
    if reading and writing:
        raise OperationError(space.w_ValueError,
                             space.wrap("cannot open in read-write mode"))
    if basemode == "a":
        raise OperationError(space.w_ValueError,
                             space.wrap("cannot append to bz2 file"))
    try:
        stream = open_path_helper(path, os_flags, False)
    except OSError, exc:
        raise wrap_oserror_as_ioerror(space, exc)
    if reading:
        bz2stream = ReadBZ2Filter(space, stream, compresslevel)
    else:
        assert writing
        bz2stream = WriteBZ2Filter(space, stream, compresslevel)
    stream = construct_stream_tower(bz2stream, buffering, universal, reading,
                                    writing)
    return space.wrap(W_Stream(space, stream))
open_file_as_stream.unwrap_spec = [ObjSpace, str, str, int, int]


class ReadBZ2Filter(Stream):

    """Standard I/O stream filter that decompresses the stream with bz2."""

    def __init__(self, space, stream, compresslevel):
        self.space = space
        self.stream = stream
        self.decompressor = W_BZ2Decompressor(space)
        self.readlength = 0
        self.buffer = ""
        self.finished = False

    def close(self):
        self.stream.close()

    def tell(self):
        return self.readlength

    def seek(self, offset, whence):
        if whence == 1:
            if offset >= 0:
                read = 0
                while read < offset:
                    read += len(self.read(offset - read))
            else:
                pos = self.readlength + offset
                self.seek(pos, 0)
        elif whence == 0:
            self.stream.seek(0, 0)
            self.decompressor = W_BZ2Decompressor(self.space)
            self.readlength = 0
            self.buffer = ""
            self.finished = False
            read = 0
            while read < offset:
                length = len(self.read(offset - read))
                read += length
                if not length:
                    break
        else:
            raise NotImplementedError

    def readall(self):
        w_result = self.decompressor.decompress(self.stream.readall())
        result = self.space.str_w(w_result)
        self.readlength += len(result)
        return result

    def read(self, n):
        # XXX not nice
        if n <= 0:
            return ''
        while not self.buffer:
            if self.finished:
                return ""
            try:
                w_read = self.decompressor.decompress(self.stream.read(n))
            except OperationError, e:
                if e.match(self.space, self.space.w_EOFError):
                    self.finished = True
                    return ""
		raise
            self.buffer = self.space.str_w(w_read)
        if len(self.buffer) >= n:
            result = self.buffer[:n]
            self.buffer = self.buffer[n:]
        else:
            result = self.buffer
            self.buffer = ""
        self.readlength += len(result)
        return result

    def try_to_find_file_descriptor(self):
        return self.stream.try_to_find_file_descriptor()

    def write(self, s):
        raise OperationError(self.space.w_IOError,
                             self.space.wrap("file is not ready for writing"))


class WriteBZ2Filter(Stream):
    """Standard I/O stream filter that compresses the stream with bz2."""

    def __init__(self, space, stream, compresslevel):
        self.stream = stream
        self.space = space
        self.compressor = W_BZ2Compressor(space, compresslevel)
        self.writtenlength = 0

    def close(self):
        self.stream.write(self.space.str_w(self.compressor.flush()))
        self.stream.close()

    def write(self, data):
        self.stream.write(self.space.str_w(self.compressor.compress(data)))
        self.writtenlength += len(data)

    def tell(self):
        return self.writtenlength

    def seek(self, offset, whence):
        raise OperationError(self.space.w_IOError,
                             self.space.wrap("seek works only while reading"))

    def read(self, n):
        raise OperationError(self.space.w_IOError,
                             self.space.wrap("file is not ready for reading"))

    def readall(self):
        raise OperationError(self.space.w_IOError,
                             self.space.wrap("file is not ready for reading"))

    def try_to_find_file_descriptor(self):
        return self.stream.try_to_find_file_descriptor()


def descr_compressor__new__(space, w_subtype, compresslevel=9):
    x = space.allocate_instance(W_BZ2Compressor, w_subtype)
    x = space.interp_w(W_BZ2Compressor, x)
    W_BZ2Compressor.__init__(x, space, compresslevel)
    return space.wrap(x)
descr_compressor__new__.unwrap_spec = [ObjSpace, W_Root, int]

class W_BZ2Compressor(Wrappable):
    """BZ2Compressor([compresslevel=9]) -> compressor object

    Create a new compressor object. This object may be used to compress
    data sequentially. If you want to compress data in one shot, use the
    compress() function instead. The compresslevel parameter, if given,
    must be a number between 1 and 9."""
    def __init__(self, space, compresslevel):
        self.space = space
        self.bzs = bz_stream()
        self.running = False
        self._init_bz2comp(compresslevel)
    __init__.unwrap_spec = ['self', ObjSpace, int]
        
    def _init_bz2comp(self, compresslevel):
        if compresslevel < 1 or compresslevel > 9:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("compresslevel must be between 1 and 9"))
                
        bzerror = libbz2.BZ2_bzCompressInit(byref(self.bzs), compresslevel, 0, 0)
        if bzerror != BZ_OK:
            _catch_bz2_error(self.space, bzerror)
        
        self.running = True
        
    def __del__(self):
        libbz2.BZ2_bzCompressEnd(byref(self.bzs))
    
    def compress(self, data):
        """compress(data) -> string

        Provide more data to the compressor object. It will return chunks of
        compressed data whenever possible. When you've finished providing data
        to compress, call the flush() method to finish the compression process,
        and return what is left in the internal buffers."""
        
        datasize = len(data)
        
        if datasize == 0:
            return self.space.wrap("")
        
        if not self.running:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("this object was already flushed"))
        
        out_bufsize = SMALLCHUNK
        out_buf = create_string_buffer(out_bufsize)
        
        in_bufsize = datasize
        in_buf = create_string_buffer(in_bufsize)
        in_buf.value = data
        
        self.bzs.next_in = cast(in_buf, POINTER(c_char))
        self.bzs.avail_in = in_bufsize
        self.bzs.next_out = cast(out_buf, POINTER(c_char))
        self.bzs.avail_out = out_bufsize
        
        temp = []
        while True:
            bzerror = libbz2.BZ2_bzCompress(byref(self.bzs), BZ_RUN)
            if bzerror != BZ_RUN_OK:
                _catch_bz2_error(self.space, bzerror)

            if self.bzs.avail_in == 0:
                break
            elif self.bzs.avail_out == 0:
                total_out = _bzs_total_out(self.bzs)
                data = "".join([out_buf[i] for i in range(total_out)])
                temp.append(data)
                
                out_bufsize = _new_buffer_size(out_bufsize)
                out_buf = create_string_buffer(out_bufsize)
                self.bzs.next_out = cast(out_buf, POINTER(c_char))
                self.bzs.avail_out = out_bufsize

        if temp:
            total_out = _bzs_total_out(self.bzs)
            data = "".join([out_buf[i] for i in range(total_out - len(temp[0]))])
            temp.append(data)
            return self.space.wrap("".join(temp))

        total_out = _bzs_total_out(self.bzs)
        res = "".join([out_buf[i] for i in range(total_out)])
        return self.space.wrap(res)
    compress.unwrap_spec = ['self', str]
    
    def flush(self):
        if not self.running:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("this object was already flushed"))
        self.running = False
        
        out_bufsize = SMALLCHUNK
        out_buf = create_string_buffer(out_bufsize)
    
        self.bzs.next_out = cast(out_buf, POINTER(c_char))
        self.bzs.avail_out = out_bufsize
        
        total_out = _bzs_total_out(self.bzs)
        
        temp = []
        while True:
            bzerror = libbz2.BZ2_bzCompress(byref(self.bzs), BZ_FINISH)
            if bzerror == BZ_STREAM_END:
                break
            elif bzerror != BZ_FINISH_OK:
                _catch_bz2_error(self.space, bzerror)
                
            if self.bzs.avail_out == 0:
                data = "".join([out_buf[i] for i in range(_bzs_total_out(self.bzs))])
                temp.append(data)
                
                out_bufsize = _new_buffer_size(out_bufsize)
                out_buf = create_string_buffer(out_bufsize)
                self.bzs.next_out = cast(out_buf, POINTER(c_char))
                self.bzs.avail_out = out_bufsize
        
        if temp:
            return self.space.wrap("".join(temp))
            
        if self.bzs.avail_out:
            size = _bzs_total_out(self.bzs) - total_out
            res = "".join([out_buf[i] for i in range(size)])
            return self.space.wrap(res)
    
        total_out = _bzs_total_out(self.bzs)
        res = "".join([out_buf[i] for i in range(total_out)])
        return self.space.wrap(res)
    flush.unwrap_spec = ['self']

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
descr_decompressor__new__.unwrap_spec = [ObjSpace, W_Root]

class W_BZ2Decompressor(Wrappable):
    """BZ2Decompressor() -> decompressor object

    Create a new decompressor object. This object may be used to decompress
    data sequentially. If you want to decompress data in one shot, use the
    decompress() function instead."""
    
    def __init__(self, space):
        self.space = space
        
        self.bzs = bz_stream()
        self.running = False
        self.unused_data = ""
        
        self._init_bz2decomp()
    
    def _init_bz2decomp(self):
        bzerror = libbz2.BZ2_bzDecompressInit(byref(self.bzs), 0, 0)
        if bzerror != BZ_OK:
            _catch_bz2_error(self.space, bzerror)
        
        self.running = True
    
    def __del__(self):
        libbz2.BZ2_bzDecompressEnd(byref(self.bzs))
    
    def decompress(self, data):
        """"decompress(data) -> string

        Provide more data to the decompressor object. It will return chunks
        of decompressed data whenever possible. If you try to decompress data
        after the end of stream is found, EOFError will be raised. If any data
        was found after the end of stream, it'll be ignored and saved in
        unused_data attribute."""
        
        if not self.running:
            raise OperationError(self.space.w_EOFError,
                self.space.wrap("end of stream was already found"))
        
        in_bufsize = len(data)
        in_buf = create_string_buffer(in_bufsize)
        in_buf.value = data

        out_bufsize = SMALLCHUNK
        out_buf = create_string_buffer(out_bufsize)
        
        self.bzs.next_in = cast(in_buf, POINTER(c_char))
        self.bzs.avail_in = in_bufsize
        self.bzs.next_out = cast(out_buf, POINTER(c_char))
        self.bzs.avail_out = out_bufsize
        
        temp = []
        while True:
            bzerror = libbz2.BZ2_bzDecompress(byref(self.bzs))
            if bzerror == BZ_STREAM_END:
                if self.bzs.avail_in != 0:
                    unused = [self.bzs.next_in[i] for i in range(self.bzs.avail_in)]
                    self.unused_data = "".join(unused)
                self.running = False
                break
            if bzerror != BZ_OK:
                _catch_bz2_error(self.space, bzerror)
            
            if self.bzs.avail_in == 0:
                break
            elif self.bzs.avail_out == 0:
                total_out = _bzs_total_out(self.bzs)
                data = "".join([out_buf[i] for i in range(total_out)])
                temp.append(data)
                
                out_bufsize = _new_buffer_size(out_bufsize)
                out_buf = create_string_buffer(out_bufsize)
                self.bzs.next_out = cast(out_buf, POINTER(c_char))
                self.bzs.avail_out = out_bufsize
                
        if temp:
            total_out = _bzs_total_out(self.bzs)
            data = "".join([out_buf[i] for i in range(total_out - len(temp[0]))])
            temp.append(data)
            return self.space.wrap("".join(temp))

        total_out = _bzs_total_out(self.bzs)
        res = "".join([out_buf[i] for i in range(total_out) if out_buf[i] != '\x00'])
        return self.space.wrap(res)
    decompress.unwrap_spec = ['self', str]


W_BZ2Decompressor.typedef = TypeDef("BZ2Decompressor",
    __doc__ = W_BZ2Decompressor.__doc__,
    __new__ = interp2app(descr_decompressor__new__),
    unused_data = interp_attrproperty("unused_data", W_BZ2Decompressor),
    decompress = interp2app(W_BZ2Decompressor.decompress),
)


def compress(space, data, compresslevel=9):
    """compress(data [, compresslevel=9]) -> string

    Compress data in one shot. If you want to compress data sequentially,
    use an instance of BZ2Compressor instead. The compresslevel parameter, if
    given, must be a number between 1 and 9."""
    
    if compresslevel < 1 or compresslevel > 9:
        raise OperationError(space.w_ValueError,
            space.wrap("compresslevel must be between 1 and 9"))
            
    bzs = bz_stream()
    
    in_bufsize = len(data)
    # conforming to bz2 manual, this is large enough to fit compressed
        # data in one shot. We will check it later anyway.
    out_bufsize = in_bufsize + (in_bufsize / 100 + 1) + 600
    
    out_buf = create_string_buffer(out_bufsize)
    in_buf = create_string_buffer(in_bufsize)
    in_buf.value = data
    
    bzs.next_in = cast(in_buf, POINTER(c_char))
    bzs.avail_in = in_bufsize
    bzs.next_out = cast(out_buf, POINTER(c_char))
    bzs.avail_out = out_bufsize

    bzerror = libbz2.BZ2_bzCompressInit(byref(bzs), compresslevel, 0, 0)
    if bzerror != BZ_OK:
        _catch_bz2_error(space, bzerror)
    
    total_out = _bzs_total_out(bzs)
    temp = []
    while True:
        bzerror = libbz2.BZ2_bzCompress(byref(bzs), BZ_FINISH)
        if bzerror == BZ_STREAM_END:
            break
        elif bzerror != BZ_FINISH_OK:
            libbz2.BZ2_bzCompressEnd(byref(bzs))
            _catch_bz2_error(space, bzerror)
            
        if bzs.avail_out == 0:
            data = "".join([out_buf[i] for i in range(_bzs_total_out(bzs))])
            temp.append(data)
            
            out_bufsize = _new_buffer_size(out_bufsize)
            out_buf = create_string_buffer(out_bufsize)
            bzs.next_out = cast(out_buf, POINTER(c_char))
            bzs.avail_out = out_bufsize
    
    if temp:
        res = "".join(temp)
        
    if bzs.avail_out:
        size = _bzs_total_out(bzs) - total_out
        res = "".join([out_buf[i] for i in range(size)])
    else:
        total_out = _bzs_total_out(bzs)
        res = "".join([out_buf[i] for i in range(total_out)])
    
    libbz2.BZ2_bzCompressEnd(byref(bzs))
    return space.wrap(res)
compress.unwrap_spec = [ObjSpace, str, int]

def decompress(space, data):
    """decompress(data) -> decompressed data

    Decompress data in one shot. If you want to decompress data sequentially,
    use an instance of BZ2Decompressor instead."""
    
    in_bufsize = len(data)
    if in_bufsize == 0:
        return space.wrap("")
    
    bzs = bz_stream()
    
    in_buf = create_string_buffer(in_bufsize)
    in_buf.value = data

    out_bufsize = SMALLCHUNK
    out_buf = create_string_buffer(out_bufsize)
    
    bzs.next_in = cast(in_buf, POINTER(c_char))
    bzs.avail_in = in_bufsize
    bzs.next_out = cast(out_buf, POINTER(c_char))
    bzs.avail_out = out_bufsize
    
    bzerror = libbz2.BZ2_bzDecompressInit(byref(bzs), 0, 0)
    if bzerror != BZ_OK:
        _catch_bz2_error(space, bzerror)
        
    temp = []
    while True:
        bzerror = libbz2.BZ2_bzDecompress(byref(bzs))
        if bzerror == BZ_STREAM_END:
            break
        if bzerror != BZ_OK:
            libbz2.BZ2_bzDecompressEnd(byref(bzs))
            _catch_bz2_error(space, bzerror)
        
        if bzs.avail_in == 0:
            libbz2.BZ2_bzDecompressEnd(byref(bzs))
            raise OperationError(space.w_ValueError,
                space.wrap("couldn't find end of stream"))
        elif bzs.avail_out == 0:
            total_out = _bzs_total_out(bzs)
            data = "".join([out_buf[i] for i in range(total_out)])
            temp.append(data)
            
            out_bufsize = _new_buffer_size(out_bufsize)
            out_buf = create_string_buffer(out_bufsize)
            bzs.next_out = cast(out_buf, POINTER(c_char))
            bzs.avail_out = out_bufsize
    
    total_out = _bzs_total_out(bzs)
    if temp:
        data = "".join([out_buf[i] for i in range(total_out - len(temp[0]))])
        temp.append(data)
        res = "".join(temp)
    else:
        res = "".join([out_buf[i] for i in range(total_out) if out_buf[i] != '\x00'])
    
    libbz2.BZ2_bzDecompressEnd(byref(bzs))
    return space.wrap(res)
decompress.unwrap_spec = [ObjSpace, str]
