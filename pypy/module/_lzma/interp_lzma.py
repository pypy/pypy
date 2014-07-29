from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty_bytes, interp_attrproperty)
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from pypy.module.thread.os_lock import Lock
from rpython.rlib.objectmodel import specialize
from rpython.rlib.rarithmetic import LONGLONG_MASK, r_ulonglong
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem import lltype
from rpython.translator.tool.cbuild import ExternalCompilationInfo


FORMAT_AUTO, FORMAT_XZ, FORMAT_ALONE, FORMAT_RAW = range(4)


eci = ExternalCompilationInfo(
    includes = ['lzma.h'],
    libraries = ['lzma'],
    )
eci = platform.configure_external_library(
    'lzma', eci,
    [dict(prefix='lzma-')])
if not eci:
    raise ImportError("Could not find lzma library")


class CConfig:
    _compilation_info_ = eci
    calling_conv = 'c'

    BUFSIZ = platform.ConstantInteger("BUFSIZ")

    lzma_stream = platform.Struct(
        'lzma_stream',
        [('next_in', rffi.CCHARP),
         ('avail_in', rffi.UINT),
         ('total_in', rffi.UINT),
         ('next_out', rffi.CCHARP),
         ('avail_out', rffi.UINT),
         ('total_out', rffi.UINT),
         ])

    lzma_options_lzma = platform.Struct(
        'lzma_options_lzma',
        [])

constant_names = '''
    LZMA_RUN LZMA_FINISH
    LZMA_OK LZMA_GET_CHECK LZMA_NO_CHECK LZMA_STREAM_END
    LZMA_PRESET_DEFAULT
    LZMA_CHECK_ID_MAX
    LZMA_TELL_ANY_CHECK LZMA_TELL_NO_CHECK
    '''.split()
for name in constant_names:
    setattr(CConfig, name, platform.ConstantInteger(name))

class cConfig(object):
    pass
for k, v in platform.configure(CConfig).items():
    setattr(cConfig, k, v)

for name in constant_names:
    globals()[name] = getattr(cConfig, name)
lzma_stream = lltype.Ptr(cConfig.lzma_stream)
lzma_options_lzma = lltype.Ptr(cConfig.lzma_options_lzma)
BUFSIZ = cConfig.BUFSIZ
LZMA_CHECK_UNKNOWN = LZMA_CHECK_ID_MAX + 1

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=
                           CConfig._compilation_info_, **kwds)

lzma_ret = rffi.INT
lzma_action = rffi.INT
lzma_bool = rffi.INT

lzma_lzma_preset = external('lzma_lzma_preset', [lzma_options_lzma, rffi.UINT], lzma_bool)
lzma_alone_encoder = external('lzma_alone_encoder', [lzma_stream, lzma_options_lzma], lzma_ret)
lzma_end = external('lzma_end', [lzma_stream], lltype.Void)

lzma_auto_decoder = external('lzma_auto_decoder', [lzma_stream, rffi.LONG, rffi.INT], lzma_ret)
lzma_get_check = external('lzma_get_check', [lzma_stream], rffi.INT)

lzma_code = external('lzma_code', [lzma_stream, lzma_action], rffi.INT)


@specialize.arg(1)
def raise_error(space, fmt, *args):
    raise oefmt(space.w_RuntimeError, fmt, *args)


def _catch_lzma_error(space, lzret):
    if (lzret == LZMA_OK or lzret == LZMA_GET_CHECK or
        lzret == LZMA_NO_CHECK or lzret == LZMA_STREAM_END):
        return
    raise raise_error(space, "Unrecognized error from liblzma: %d", lzret)


if BUFSIZ < 8192:
    SMALLCHUNK = 8192
else:
    SMALLCHUNK = BUFSIZ
if rffi.sizeof(rffi.INT) > 4:
    BIGCHUNK = 512 * 32
else:
    BIGCHUNK = 512 * 1024


def _new_buffer_size(current_size):
    # keep doubling until we reach BIGCHUNK; then the buffer size is no
    # longer increased
    if current_size < BIGCHUNK:
        return current_size + current_size
    return current_size


class OutBuffer(object):
    """Handler for the output buffer.  A bit custom code trying to
    encapsulate the logic of setting up the fields of 'lzs' and
    allocating raw memory as needed.
    """
    def __init__(self, lzs, initial_size=SMALLCHUNK):
        # when the constructor is called, allocate a piece of memory
        # of length 'piece_size' and make lzs ready to dump there.
        self.temp = []
        self.lzs = lzs
        self._allocate_chunk(initial_size)

    def _allocate_chunk(self, size):
        self.raw_buf, self.gc_buf = rffi.alloc_buffer(size)
        self.current_size = size
        self.lzs.c_next_out = self.raw_buf
        rffi.setintfield(self.lzs, 'c_avail_out', size)

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
        count_unoccupied = rffi.getintfield(self.lzs, 'c_avail_out')
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


class W_LZMACompressor(W_Root):
    def __init__(self, space, format):
        self.format = format
        self.lock = Lock(space)
        self.flushed = False
        self.lzs = lltype.malloc(lzma_stream.TO, flavor='raw', zero=True)

    def __del__(self):
        lzma_end(self.lzs)
        lltype.free(self.lzs, flavor='raw')

    def _init_alone(self, space, preset, w_filters):
        if space.is_none(w_filters):
            with lltype.scoped_alloc(lzma_options_lzma.TO) as options:
                if lzma_lzma_preset(options, preset):
                    raise_error(space, "Invalid compression preset: %d", preset)
                lzret = lzma_alone_encoder(self.lzs, options)
        else:
            raise NotImplementedError
        _catch_lzma_error(space, lzret)

    @staticmethod
    @unwrap_spec(format=int,
                 w_check=WrappedDefault(None),
                 w_preset=WrappedDefault(None), 
                 w_filters=WrappedDefault(None))
    def descr_new_comp(space, w_subtype, format=FORMAT_XZ, 
                       w_check=None, w_preset=None, w_filters=None):
        w_self = space.allocate_instance(W_LZMACompressor, w_subtype)
        self = space.interp_w(W_LZMACompressor, w_self)
        W_LZMACompressor.__init__(self, space, format)

        if space.is_none(w_preset):
            preset = LZMA_PRESET_DEFAULT
        else:
            preset = space.int_w(w_preset)

        if format == FORMAT_ALONE:
            self._init_alone(space, preset, w_filters)
        else:
            raise NotImplementedError

        return w_self

    @unwrap_spec(data='bufferstr')
    def compress_w(self, space, data):
        with self.lock:
            if self.flushed:
                raise oefmt(space.w_ValueError, "Compressor has been flushed")
            result = self._compress(space, data, LZMA_RUN)
        return space.wrapbytes(result)

    def flush_w(self, space):
        with self.lock:
            if self.flushed:
                raise oefmt(space.w_ValueError, "Repeated call to flush()")
            result = self._compress(space, "", LZMA_FINISH)
        return space.wrapbytes(result)

    def _compress(self, space, data, action):
        datasize = len(data)
        with lltype.scoped_alloc(rffi.CCHARP.TO, datasize) as in_buf:
            for i in range(datasize):
                in_buf[i] = data[i]

            with OutBuffer(self.lzs) as out:
                self.lzs.c_next_in = in_buf
                rffi.setintfield(self.lzs, 'c_avail_in', datasize)

                while True:
                    lzret = lzma_code(self.lzs, action)
                    _catch_lzma_error(space, lzret)

                    if (action == LZMA_RUN and
                        rffi.getintfield(self.lzs, 'c_avail_in') == 0):
                        break
                    if action == LZMA_FINISH and lzret == LZMA_STREAM_END:
                        break
                    elif rffi.getintfield(self.lzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                return out.make_result_string()


W_LZMACompressor.typedef = TypeDef("LZMACompressor",
    __new__ = interp2app(W_LZMACompressor.descr_new_comp),
    compress = interp2app(W_LZMACompressor.compress_w),
    flush = interp2app(W_LZMACompressor.flush_w),
)


class W_LZMADecompressor(W_Root):
    def __init__(self, space, format):
        self.format = format
        self.lock = Lock(space)
        self.eof = False
        self.lzs = lltype.malloc(lzma_stream.TO, flavor='raw', zero=True)
        self.check = LZMA_CHECK_UNKNOWN
        self.unused_data = ''

    def __del__(self):
        lzma_end(self.lzs)
        lltype.free(self.lzs, flavor='raw')

    @staticmethod
    @unwrap_spec(format=int,
                 w_memlimit=WrappedDefault(None),
                 w_filters=WrappedDefault(None))
    def descr_new_dec(space, w_subtype, format=FORMAT_AUTO,
                      w_memlimit=None, w_filters=None):
        w_self = space.allocate_instance(W_LZMADecompressor, w_subtype)
        self = space.interp_w(W_LZMADecompressor, w_self)
        W_LZMADecompressor.__init__(self, space, format)

        if space.is_none(w_memlimit):
            memlimit = r_ulonglong(LONGLONG_MASK)
        else:
            memlimit = space.r_ulonglong_w(w_memlimit)

        decoder_flags = LZMA_TELL_ANY_CHECK | LZMA_TELL_NO_CHECK

        if format == FORMAT_AUTO:
            lzret = lzma_auto_decoder(self.lzs, memlimit, decoder_flags)
            _catch_lzma_error(space, lzret)
        else:
            raise NotImplementedError

        return w_self

    @unwrap_spec(data='bufferstr')
    def decompress_w(self, space, data):
        with self.lock:
            if self.eof:
                raise oefmt(space.w_EOFError, "Already at end of stream")
            result = self._decompress(space, data)
        return space.wrapbytes(result)

    def _decompress(self, space, data):
        datasize = len(data)

        with lltype.scoped_alloc(rffi.CCHARP.TO, datasize) as in_buf:
            for i in range(datasize):
                in_buf[i] = data[i]

            with OutBuffer(self.lzs) as out:
                self.lzs.c_next_in = in_buf
                rffi.setintfield(self.lzs, 'c_avail_in', datasize)

                while True:
                    lzret = lzma_code(self.lzs, LZMA_RUN)
                    _catch_lzma_error(space, lzret)
                    if lzret == LZMA_GET_CHECK or lzret == LZMA_NO_CHECK:
                        self.check = lzma_get_check(self.lzs)
                    if lzret == LZMA_STREAM_END:
                        self.eof = True
                        if rffi.getintfield(self.lzs, 'c_avail_in') > 0:
                            unused = [self.lzs.c_next_in[i]
                                      for i in range(
                                    rffi.getintfield(self.lzs,
                                                     'c_avail_in'))]
                            self.unused_data = "".join(unused)
                            break
                    if rffi.getintfield(self.lzs, 'c_avail_in') == 0:
                        break
                    elif rffi.getintfield(self.lzs, 'c_avail_out') == 0:
                        out.prepare_next_chunk()

                return out.make_result_string()


W_LZMADecompressor.typedef = TypeDef("LZMADecompressor",
    __new__ = interp2app(W_LZMADecompressor.descr_new_dec),
    decompress = interp2app(W_LZMADecompressor.decompress_w),
    eof = interp_attrproperty("eof", W_LZMADecompressor),
    unused_data = interp_attrproperty_bytes("unused_data", W_LZMADecompressor),
)


def encode_filter_properties(space, w_filter):
    """Return a bytes object encoding the options (properties) of the filter
       specified by *filter* (a dict).

    The result does not include the filter ID itself, only the options.
    """

def decode_filter_properties(space, w_filter_id, w_encoded_props):
    """Return a dict describing a filter with ID *filter_id*, and options
       (properties) decoded from the bytes object *encoded_props*.
    """
    
