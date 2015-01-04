# This file was copied from lzmaffi version 0.3.0.
# It is an almost exact copy of lzmaffi/_lzmamodule2.py.

# PyPy changes:
# - added __getstate__() methods that raise TypeError on pickling.
# - in ffi.verify(), changed modulename to '_lzmaffi'.

from cffi import FFI
import threading
import functools
import collections
import weakref
import sys
import io

SUPPORTED_STREAM_FLAGS_VERSION = 0

__all__ = ['CHECK_CRC32',
 'CHECK_CRC64',
 'CHECK_ID_MAX',
 'CHECK_NONE',
 'CHECK_SHA256',
 'CHECK_UNKNOWN',
 'FILTER_ARM',
 'FILTER_ARMTHUMB',
 'FILTER_DELTA',
 'FILTER_IA64',
 'FILTER_LZMA1',
 'FILTER_LZMA2',
 'FILTER_POWERPC',
 'FILTER_SPARC',
 'FILTER_X86',
 'FORMAT_ALONE',
 'FORMAT_AUTO',
 'FORMAT_RAW',
 'FORMAT_XZ',
 'FORMAT_BLOCK',
 'LZMACompressor',
 'LZMADecompressor',
 'LZMAError',
 'MF_BT2',
 'MF_BT3',
 'MF_BT4',
 'MF_HC3',
 'MF_HC4',
 'MODE_FAST',
 'MODE_NORMAL',
 'PRESET_DEFAULT',
 'PRESET_EXTREME',
 'STREAM_HEADER_SIZE',
 'decode_block_header_size',
 'decode_stream_header',
 'decode_stream_footer',
 'decode_index',
 '_decode_filter_properties',
 '_encode_filter_properties',
 'is_check_supported']

_owns = weakref.WeakKeyDictionary()

ffi = FFI()
ffi.cdef("""
#define UINT64_MAX ...
#define LZMA_CONCATENATED ...
#define LZMA_CHECK_NONE ...
#define LZMA_CHECK_CRC32 ...
#define LZMA_CHECK_CRC64 ...
#define LZMA_CHECK_SHA256 ...
#define LZMA_CHECK_ID_MAX ...
#define LZMA_DELTA_TYPE_BYTE ...
#define LZMA_TELL_ANY_CHECK ...
#define LZMA_TELL_NO_CHECK ...
#define LZMA_VLI_UNKNOWN ...
#define LZMA_FILTER_LZMA1 ...
#define LZMA_FILTER_LZMA2 ...
#define LZMA_FILTER_DELTA ...
#define LZMA_FILTER_X86 ...
#define LZMA_FILTER_IA64 ...
#define LZMA_FILTER_ARM ...
#define LZMA_FILTER_ARMTHUMB ...
#define LZMA_FILTER_SPARC ...
#define LZMA_FILTER_POWERPC ...
#define LZMA_FILTERS_MAX ...
#define LZMA_STREAM_HEADER_SIZE ...
#define LZMA_MF_HC3 ...
#define LZMA_MF_HC4 ...
#define LZMA_MF_BT2 ...
#define LZMA_MF_BT3 ...
#define LZMA_MF_BT4 ...
#define LZMA_MODE_FAST ...
#define LZMA_MODE_NORMAL ...
#define LZMA_PRESET_DEFAULT ...
#define LZMA_PRESET_EXTREME ...

enum lzma_ret { LZMA_OK, LZMA_STREAM_END, LZMA_NO_CHECK,
    LZMA_UNSUPPORTED_CHECK, LZMA_GET_CHECK,
    LZMA_MEM_ERROR, LZMA_MEMLIMIT_ERROR,
    LZMA_FORMAT_ERROR, LZMA_OPTIONS_ERROR,
    LZMA_DATA_ERROR, LZMA_BUF_ERROR,
    LZMA_PROG_ERROR, ... };

enum lzma_action { LZMA_RUN, LZMA_FINISH, ...};

enum lzma_check { ... };

typedef uint64_t lzma_vli;

typedef struct {
    void* (*alloc)(void*, size_t, size_t);
    void (*free)(void*, void*);
    void* opaque;
    ...;
} lzma_allocator;

typedef struct {
    const uint8_t *next_in;
    size_t avail_in;
    uint64_t total_in;

    uint8_t *next_out;
    size_t avail_out;
    uint64_t total_out;
    lzma_allocator *allocator;
    ...;
} lzma_stream;

typedef struct {
    int type;
    uint32_t dist;
    ...;
} lzma_options_delta;

typedef struct {
    uint32_t start_offset;
    ...;
} lzma_options_bcj;

typedef struct {
    uint32_t dict_size;
    uint32_t lc;
    uint32_t lp;
    uint32_t pb;
    int mode;
    uint32_t nice_len;
    int mf;
    uint32_t depth;
    ...;
} lzma_options_lzma;

typedef struct {
    lzma_vli id;
    void *options;
    ...;
} lzma_filter;

typedef struct {
    uint32_t version;
    lzma_vli backward_size;
    int check;
    ...;
} lzma_stream_flags;

typedef ... lzma_index;

typedef struct {
    uint32_t version;
    uint32_t header_size;
    int check;
    lzma_vli compressed_size;
    lzma_filter* filters;
    ...;
} lzma_block;

bool lzma_check_is_supported(int check);

// Encoder/Decoder
int lzma_auto_decoder(lzma_stream *strm, uint64_t memlimit, uint32_t flags);
int lzma_stream_decoder(lzma_stream *strm, uint64_t memlimit, uint32_t flags);
int lzma_alone_decoder(lzma_stream *strm, uint64_t memlimit);
int lzma_raw_decoder(lzma_stream *strm, const lzma_filter *filters);
int lzma_block_decoder(lzma_stream *strm, lzma_block *block);

int lzma_easy_encoder(lzma_stream *strm, uint32_t preset, int check);
int lzma_alone_encoder(lzma_stream *strm, lzma_options_lzma* options);
int lzma_raw_encoder(lzma_stream *strm, const lzma_filter *filters);

int lzma_get_check(const lzma_stream *strm);

int lzma_code(lzma_stream *strm, int action);

void lzma_end(lzma_stream *strm);

// Extras
int lzma_stream_header_decode(lzma_stream_flags *options, const uint8_t *in);
int lzma_stream_footer_decode(lzma_stream_flags *options, const uint8_t *in);
int lzma_stream_flags_compare(const lzma_stream_flags *a,
    const lzma_stream_flags *b);

enum lzma_index_iter_mode { LZMA_INDEX_ITER_ANY, LZMA_INDEX_ITER_STREAM,
    LZMA_INDEX_ITER_BLOCK, LZMA_INDEX_ITER_NONEMPTY_BLOCK, ... };

// Indexes
lzma_index* lzma_index_init(lzma_allocator *al);
void lzma_index_end(lzma_index *i, lzma_allocator *al);
int lzma_index_stream_padding(lzma_index *i, lzma_vli stream_padding);
lzma_index* lzma_index_dup(const lzma_index *i, lzma_allocator *al);
int lzma_index_cat(lzma_index *dest, lzma_index *src, lzma_allocator *al);
int lzma_index_buffer_decode(lzma_index **i, uint64_t *memlimit,
    lzma_allocator *allocator, const uint8_t *in, size_t *in_pos,
    size_t in_size);
lzma_vli lzma_index_block_count(const lzma_index *i);
lzma_vli lzma_index_stream_size(const lzma_index *i);
lzma_vli lzma_index_uncompressed_size(const lzma_index *i);
lzma_vli lzma_index_size(const lzma_index *i);
lzma_vli lzma_index_total_size(const lzma_index *i);

// Blocks
int lzma_block_header_decode(lzma_block *block, lzma_allocator *al,
    const uint8_t *in);
int lzma_block_compressed_size(lzma_block *block, lzma_vli unpadded_size);

typedef struct {
    // cffi doesn't support partial anonymous structs
    // so we write the definition in full
	struct {
		const lzma_stream_flags *flags;
		const void *reserved_ptr1;
		const void *reserved_ptr2;
		const void *reserved_ptr3;
		lzma_vli number;
		lzma_vli block_count;
		lzma_vli compressed_offset;
		lzma_vli uncompressed_offset;
		lzma_vli compressed_size;
		lzma_vli uncompressed_size;
		lzma_vli padding;
		lzma_vli reserved_vli1;
		lzma_vli reserved_vli2;
		lzma_vli reserved_vli3;
		lzma_vli reserved_vli4;
	} stream;
	struct {
		lzma_vli number_in_file;
		lzma_vli compressed_file_offset;
		lzma_vli uncompressed_file_offset;
		lzma_vli number_in_stream;
		lzma_vli compressed_stream_offset;
		lzma_vli uncompressed_stream_offset;
		lzma_vli uncompressed_size;
		lzma_vli unpadded_size;
		lzma_vli total_size;
		lzma_vli reserved_vli1;
		lzma_vli reserved_vli2;
		lzma_vli reserved_vli3;
		lzma_vli reserved_vli4;
		const void *reserved_ptr1;
		const void *reserved_ptr2;
		const void *reserved_ptr3;
		const void *reserved_ptr4;
	} block;
    ...;
} lzma_index_iter;

void lzma_index_iter_init(lzma_index_iter *iter, const lzma_index *i);
int lzma_index_iter_next(lzma_index_iter *iter, int mode);
int lzma_index_iter_locate(lzma_index_iter *iter, lzma_vli target);

// Properties
int lzma_properties_size(uint32_t *size, const lzma_filter *filter);
int lzma_properties_encode(const lzma_filter *filter, uint8_t *props);
int lzma_properties_decode(lzma_filter *filter, lzma_allocator *allocator,
    const uint8_t *props, size_t props_size);
int lzma_lzma_preset(lzma_options_lzma* options, uint32_t preset);

// Special functions
void _pylzma_stream_init(lzma_stream *strm);
void _pylzma_block_header_size_decode(uint32_t b);

void *malloc(size_t size);
void free(void *ptr);
void *realloc(void *ptr, size_t size);
""")

m = ffi.verify("""
#include <lzma.h>
#include <stdlib.h>
void _pylzma_stream_init(lzma_stream *strm) {
    lzma_stream tmp = LZMA_STREAM_INIT; // macro from lzma.h
    *strm = tmp;
}

uint32_t _pylzma_block_header_size_decode(uint32_t b) {
    return lzma_block_header_size_decode(b); // macro from lzma.h
}
""",
    libraries=['lzma'],
    include_dirs=['/opt/local/include', '/usr/local/include'],
    library_dirs=['/opt/local/include', '/usr/local/include'],
    ext_package='_lzmaffi_mods',
    modulename='_lzmaffi')

def _new_lzma_stream():
    ret = ffi.new('lzma_stream*')
    m._pylzma_stream_init(ret)
    return ffi.gc(ret, m.lzma_end)

def add_constant(c):
    globals()[c] = getattr(m, 'LZMA_' + c)

if sys.version_info >= (2,7):
    def to_bytes(data):
        return memoryview(data).tobytes()
else:
    def to_bytes(data):
        if not isinstance(data, basestring):
            raise TypeError("lzma: must be str/unicode, got %s" % (type(data),))
        return bytes(data)

if sys.version_info >= (3,0):
    long = int

for c in ['CHECK_CRC32', 'CHECK_CRC64', 'CHECK_ID_MAX', 'CHECK_NONE', 'CHECK_SHA256', 'FILTER_ARM', 'FILTER_ARMTHUMB', 'FILTER_DELTA', 'FILTER_IA64', 'FILTER_LZMA1', 'FILTER_LZMA2', 'FILTER_POWERPC', 'FILTER_SPARC', 'FILTER_X86', 'MF_BT2', 'MF_BT3', 'MF_BT4', 'MF_HC3', 'MF_HC4', 'MODE_FAST', 'MODE_NORMAL', 'PRESET_DEFAULT', 'PRESET_EXTREME', 'STREAM_HEADER_SIZE']:
    add_constant(c)

def _parse_format(format):
    if isinstance(format, (int, long)):
        return format
    else:
        raise TypeError

CHECK_UNKNOWN = CHECK_ID_MAX + 1
FORMAT_AUTO, FORMAT_XZ, FORMAT_ALONE, FORMAT_RAW, FORMAT_BLOCK = range(5)

BCJ_FILTERS = (m.LZMA_FILTER_X86,
    m.LZMA_FILTER_POWERPC,
    m.LZMA_FILTER_IA64,
    m.LZMA_FILTER_ARM,
    m.LZMA_FILTER_ARMTHUMB,
    m.LZMA_FILTER_SPARC)

class LZMAError(Exception):
    """Call to liblzma failed."""

def is_check_supported(check):
    """is_check_supported(check_id) -> bool
    
    Test whether the given integrity check is supported.
    
    Always returns True for CHECK_NONE and CHECK_CRC32."""
    return bool(m.lzma_check_is_supported(check))

def catch_lzma_error(fun, *args):
    try:
        lzret = fun(*args)
    except:
        raise
    if lzret in (m.LZMA_OK, m.LZMA_GET_CHECK, m.LZMA_NO_CHECK, m.LZMA_STREAM_END):
        return lzret
    elif lzret == m.LZMA_DATA_ERROR:
        raise LZMAError("Corrupt input data")
    elif lzret == m.LZMA_UNSUPPORTED_CHECK:
        raise LZMAError("Unsupported integrity check")
    elif lzret == m.LZMA_FORMAT_ERROR:
        raise LZMAError("Input format not supported by decoder")
    elif lzret == m.LZMA_OPTIONS_ERROR:
        raise LZMAError("Invalid or unsupported options")
    elif lzret == m.LZMA_BUF_ERROR:
        raise LZMAError("Insufficient buffer space")
    elif lzret == m.LZMA_PROG_ERROR:
        raise LZMAError("Internal error")
    elif lzret == m.LZMA_MEM_ERROR:
        raise MemoryError
    else:
        raise LZMAError("Unrecognised error from liblzma: %d" % lzret)

def parse_filter_spec_delta(id, dist=1):
    ret = ffi.new('lzma_options_delta*')
    ret.type = m.LZMA_DELTA_TYPE_BYTE
    ret.dist = dist
    return ret

def parse_filter_spec_bcj(id, start_offset=0):
    ret = ffi.new('lzma_options_bcj*')
    ret.start_offset = start_offset
    return ret

def parse_filter_spec_lzma(id, preset=m.LZMA_PRESET_DEFAULT, **kwargs):
    ret = ffi.new('lzma_options_lzma*')
    if m.lzma_lzma_preset(ret, preset):
        raise LZMAError("Invalid...")
    for arg, val in kwargs.items():
        if arg in ('dict_size', 'lc', 'lp', 'pb', 'nice_len', 'depth'):
            setattr(ret, arg, val)
        elif arg in ('mf', 'mode'):
            setattr(ret, arg, int(val))
        else:
            raise ValueError("Invalid...")
    return ret

def parse_filter_spec(spec):
    if not isinstance(spec, collections.Mapping):
        raise TypeError("Filter...")
    ret = ffi.new('lzma_filter*')
    try:
        ret.id = spec['id']
    except KeyError:
        raise ValueError("Filter...")
    if ret.id in (m.LZMA_FILTER_LZMA1, m.LZMA_FILTER_LZMA2):
        try:
            options = parse_filter_spec_lzma(**spec)
        except TypeError:
            raise ValueError("Invalid...")
    elif ret.id == m.LZMA_FILTER_DELTA:
        try:
            options = parse_filter_spec_delta(**spec)
        except TypeError:
            raise ValueError("Invalid...")
    elif ret.id in BCJ_FILTERS:
        try:
            options = parse_filter_spec_bcj(**spec)
        except TypeError:
            raise ValueError("Invalid...")
    else:
        raise ValueError("Invalid %d" % (ret.id,))

    ret.options = options
    _owns[ret] = options
    return ret

def _encode_filter_properties(filterspec):
    """_encode_filter_properties(filter) -> bytes

    Return a bytes object encoding the options (properties) of the filter
    specified by *filter* (a dict).

    The result does not include the filter ID itself, only the options."""
    filter = parse_filter_spec(filterspec)
    size = ffi.new("uint32_t*")
    catch_lzma_error(m.lzma_properties_size, size, filter)
    result = ffi.new('char[]', size[0])
    catch_lzma_error(m.lzma_properties_encode, filter, result)
    return ffi.buffer(result)[:]

def parse_filter_chain_spec(filterspecs):
    if len(filterspecs) > m.LZMA_FILTERS_MAX:
        raise ValueError("Too...")
    filters = ffi.new('lzma_filter[]', m.LZMA_FILTERS_MAX+1)
    _owns[filters] = children = []
    for i in range(m.LZMA_FILTERS_MAX+1):
        try:
            filterspec = filterspecs[i]
        except KeyError:
            raise TypeError
        except IndexError:
            filters[i].id = m.LZMA_VLI_UNKNOWN
        else:
            filter = parse_filter_spec(filterspecs[i])
            children.append(filter)
            filters[i].id = filter.id
            filters[i].options = filter.options
    return filters

def build_filter_spec(filter):
    spec = {'id': filter.id}
    def add_opts(options_type, *opts):
        options = ffi.cast('%s*' % (options_type,), filter.options)
        for v in opts:
            spec[v] = getattr(options, v)
    if filter.id == m.LZMA_FILTER_LZMA1:
        add_opts('lzma_options_lzma', 'lc', 'lp', 'pb', 'dict_size')
    elif filter.id == m.LZMA_FILTER_LZMA2:
        add_opts('lzma_options_lzma', 'dict_size')
    elif filter.id == m.LZMA_FILTER_DELTA:
        add_opts('lzma_options_delta', 'dist')
    elif filter.id in BCJ_FILTERS:
        add_opts('lzma_options_bcj', 'start_offset')
    else:
        raise ValueError("Invalid...")
    return spec

def _decode_filter_properties(filter_id, encoded_props):
    """_decode_filter_properties(filter_id, encoded_props) -> dict

    Return a dict describing a filter with ID *filter_id*, and options
    (properties) decoded from the bytes object *encoded_props*."""
    filter = ffi.new('lzma_filter*')
    filter.id = filter_id
    catch_lzma_error(m.lzma_properties_decode,
        filter, ffi.NULL, encoded_props, len(encoded_props))
    try:
        return build_filter_spec(filter)
    finally:
        # TODO do we need this, the only use of m.free?
        m.free(filter.options)

def _decode_stream_header_or_footer(decode_f, in_bytes):
    footer_o = ffi.new('char[]', to_bytes(in_bytes))
    stream_flags = ffi.new('lzma_stream_flags*')
    catch_lzma_error(decode_f, stream_flags, footer_o)
    return StreamFlags(stream_flags)

decode_stream_footer = functools.partial(_decode_stream_header_or_footer,
    m.lzma_stream_footer_decode)

decode_stream_header = functools.partial(_decode_stream_header_or_footer,
    m.lzma_stream_header_decode)

def decode_block_header_size(in_byte):
    # lzma_block_header_size_decode(b) (((uint32_t)(b) + 1) * 4)
    return (ord(in_byte) + 1) * 4

def decode_index(s, stream_padding=0):
    indexp = ffi.new('lzma_index**')
    memlimit = ffi.new('uint64_t*')
    memlimit[0] = m.UINT64_MAX
    allocator = ffi.NULL
    in_buf = ffi.new('char[]', to_bytes(s))
    in_pos = ffi.new('size_t*')
    in_pos[0] = 0
    catch_lzma_error(m.lzma_index_buffer_decode, indexp,
        memlimit, allocator, in_buf, in_pos, len(s))
    return Index(indexp[0], allocator, stream_padding)

class Index(object):
    def __init__(self, i, allocator, stream_padding=0):
        self.i = i
        self.allocator = allocator
        m.lzma_index_stream_padding(i, stream_padding)

    @property
    def uncompressed_size(self):
        return m.lzma_index_uncompressed_size(self.i)

    @property
    def block_count(self):
        return m.lzma_index_block_count(self.i)

    @property
    def index_size(self):
        return m.lzma_index_size(self.i)

    @property
    def blocks_size(self):
        return m.lzma_index_total_size(self.i)

    def __iter__(self):
        return self.iterator()

    def iterator(self, type=m.LZMA_INDEX_ITER_BLOCK):
        iterator = ffi.new('lzma_index_iter*')
        m.lzma_index_iter_init(iterator, self.i)
        while not m.lzma_index_iter_next(iterator, type):
            yield (IndexStreamData(iterator.stream), IndexBlockData(iterator.block))

    def find(self, offset):
        iterator = ffi.new('lzma_index_iter*')
        m.lzma_index_iter_init(iterator, self.i)
        if m.lzma_index_iter_locate(iterator, offset):
            # offset too high
            return None
        return (IndexStreamData(iterator.stream), IndexBlockData(iterator.block))

    def __del__(self):
        m.lzma_index_end(self.i, self.allocator)

    def copy(self):
        new_i = m.lzma_index_dup(self.i, self.allocator)
        return Index(new_i, self.allocator)

    deepcopy = copy

    def append(self, other_index):
        # m.lzma_index_cat frees its second parameter so we
        # must copy it first
        other_index_i = m.lzma_index_dup(other_index.i, self.allocator)
        catch_lzma_error(m.lzma_index_cat, self.i, 
            other_index_i, self.allocator)

class _StructToPy(object):
    __slots__ = ()
    def __init__(self, struct_obj):
        # TODO make PyPy-fast
        for attr in self.__slots__:
            setattr(self, attr, getattr(struct_obj, attr))
    def __repr__(self):
        descriptions = ('%s=%r' % (attr, getattr(self, attr)) for attr in self.__slots__)
        return "<%s %s>" % (type(self).__name__, ' '.join(descriptions))

class IndexStreamData(_StructToPy):
    __slots__ = ('number', 'block_count', 'compressed_offset', 'uncompressed_offset',
        'compressed_size', 'uncompressed_size')

class IndexBlockData(_StructToPy):
    __slots__ = ('number_in_file', 'compressed_file_offset', 'uncompressed_file_offset',
        'compressed_stream_offset', 'uncompressed_stream_offset',
        'uncompressed_size', 'unpadded_size', 'total_size')

class StreamFlags(object):
    def __init__(self, i):
        self.i = i

    version = property(lambda self: self.i.version)
    check = property(lambda self: self.i.check)
    backward_size = property(lambda self: self.i.backward_size)

    @property
    def supported(self):
        return self.version > SUPPORTED_STREAM_FLAGS_VERSION

    def check_supported(self):
        if not self.supported:
            raise LZMAError("Stream is too new for liblzma version")

    def matches(self, other):
        return m.lzma_stream_flags_compare(self.i, other.i) == m.LZMA_OK

    def copy(self):
        other_i = ffi.new('lzma_stream_flags*', self.i)
        return StreamFlags(other_i)

class Allocator(object):
    def __init__(self):
        self.owns = {}
        self.lzma_allocator = ffi.new('lzma_allocator*')
        alloc = self.owns['a'] = ffi.callback("void*(void*, size_t, size_t)", self.__alloc)
        free = self.owns['b'] = ffi.callback("void(void*, void*)", self.__free)
        self.lzma_allocator.alloc = alloc
        self.lzma_allocator.free = free
        self.lzma_allocator.opaque = ffi.NULL
    def __alloc(self, _opaque, _nmemb, size):
        new_mem = ffi.new('char[]', size)
        self.owns[self._addr(new_mem)] = new_mem
        return new_mem
    def _addr(self, ptr):
        return long(ffi.cast('uintptr_t', ptr))
    def __free(self, _opaque, ptr):
        if self._addr(ptr) == 0: return
        del self.owns[self._addr(ptr)]

class LZMADecompressor(object):
    """
    LZMADecompressor(format=FORMAT_AUTO, memlimit=None, filters=None)

    Create a decompressor object for decompressing data incrementally.

    format specifies the container format of the input stream. If this is
    FORMAT_AUTO (the default), the decompressor will automatically detect
    whether the input is FORMAT_XZ or FORMAT_ALONE. Streams created with
    FORMAT_RAW cannot be autodetected.

    memlimit can be specified to limit the amount of memory used by the
    decompressor. This will cause decompression to fail if the input
    cannot be decompressed within the given limit.

    filters specifies a custom filter chain. This argument is required for
    FORMAT_RAW, and not accepted with any other format. When provided,
    this should be a sequence of dicts, each indicating the ID and options
    for a single filter.

    For one-shot decompression, use the decompress() function instead.
    """
    def __init__(self, format=FORMAT_AUTO, memlimit=None, filters=None, header=None, check=None, unpadded_size=None):
        decoder_flags = m.LZMA_TELL_ANY_CHECK | m.LZMA_TELL_NO_CHECK
        #decoder_flags = 0
        if memlimit is not None:
            if format == FORMAT_RAW:
                raise ValueError("Cannot sp...")
            #memlimit = long(memlimit)
        else:
            memlimit = m.UINT64_MAX

        if format == FORMAT_RAW and filters is None:
            raise ValueError("Must...")
        elif format != FORMAT_RAW and filters is not None:
            raise ValueError("Cannot...")

        if format == FORMAT_BLOCK and (header is None or unpadded_size is None or check is None):
            raise ValueError("Must...")
        elif format != FORMAT_BLOCK and (header is not None or unpadded_size is not None or check is not None):
            raise ValueError("Cannot...")

        format = _parse_format(format)
        self.lock = threading.Lock()
        self.check = CHECK_UNKNOWN
        self.unused_data = b''
        self.eof = False
        self.lzs = _new_lzma_stream()
        self._bufsiz = max(8192, io.DEFAULT_BUFFER_SIZE)

        if format == FORMAT_AUTO:
            catch_lzma_error(m.lzma_auto_decoder, self.lzs, memlimit, decoder_flags)
        elif format == FORMAT_XZ:
            catch_lzma_error(m.lzma_stream_decoder, self.lzs, memlimit, decoder_flags)
        elif format == FORMAT_ALONE:
            self.check = CHECK_NONE
            catch_lzma_error(m.lzma_alone_decoder, self.lzs, memlimit)
        elif format == FORMAT_RAW:
            self.check = CHECK_NONE
            filters = parse_filter_chain_spec(filters)
            catch_lzma_error(m.lzma_raw_decoder, self.lzs,
                filters)
        elif format == FORMAT_BLOCK:
            self.__block = block = ffi.new('lzma_block*')
            block.version = 0
            block.check = check
            block.header_size = len(header)
            block.filters = self.__filters = ffi.new('lzma_filter[]', m.LZMA_FILTERS_MAX+1)
            header_b = ffi.new('char[]', to_bytes(header))
            catch_lzma_error(m.lzma_block_header_decode, block, self.lzs.allocator, header_b)
            if unpadded_size is not None:
                catch_lzma_error(m.lzma_block_compressed_size, block, unpadded_size)
            self.expected_size = block.compressed_size
            catch_lzma_error(m.lzma_block_decoder, self.lzs, block)
        else:
            raise ValueError("invalid...")

    def decompress(self, data):
        """
        decompress(data) -> bytes

        Provide data to the decompressor object. Returns a chunk of
        decompressed data if possible, or b"" otherwise.

        Attempting to decompress data after the end of the stream is
        reached raises an EOFError. Any data found after the end of the
        stream is ignored, and saved in the unused_data attribute.
        """
        with self.lock:
            if self.eof:
                raise EOFError("Already...")
            return self._decompress(data)

    def _decompress(self, data):
        lzs = self.lzs

        # we need in_ so that lzs.next_in doesn't get garbage collected until
        # in_ goes out of scope
        data = to_bytes(data)
        lzs.next_in = in_ = ffi.new('char[]', data)
        lzs.avail_in = len(data)

        bufsiz = self._bufsiz

        lzs.next_out = orig_out = m.malloc(bufsiz)
        if orig_out == ffi.NULL:
            raise MemoryError

        lzs.avail_out = bufsiz

        data_size = 0

        try:
            while True:
                ret = catch_lzma_error(m.lzma_code, lzs, m.LZMA_RUN)
                data_size = int(ffi.cast('uintptr_t', lzs.next_out)) - int(ffi.cast('uintptr_t', orig_out))
                # data_size is the amount lzma_code has already outputted

                if ret in (m.LZMA_NO_CHECK, m.LZMA_GET_CHECK):
                    self.check = m.lzma_get_check(lzs)

                if ret == m.LZMA_STREAM_END:
                    self.eof = True
                    if lzs.avail_in > 0:
                        self.unused_data = ffi.buffer(lzs.next_in, lzs.avail_in)[:]
                    break
                elif lzs.avail_in == 0:
                    # it ate everything
                    break
                elif lzs.avail_out == 0:
                    # ran out of space in the output buffer, let's grow it
                    bufsiz += (bufsiz >> 3) + 6
                    next_out = m.realloc(orig_out, bufsiz)
                    if next_out == ffi.NULL:
                        # realloc unsuccessful
                        m.free(orig_out)
                        orig_out = ffi.NULL
                        raise MemoryError

                    orig_out = next_out

                    lzs.next_out = orig_out + data_size
                    lzs.avail_out = bufsiz - data_size

            result = ffi.buffer(orig_out, data_size)[:]
        finally:
            m.free(orig_out)

        return result

    def __getstate__(self):
        raise TypeError("cannot serialize '%s' object" %
                        self.__class__.__name__)

class LZMACompressor(object):
    """
    LZMACompressor(format=FORMAT_XZ, check=-1, preset=None, filters=None)

    Create a compressor object for compressing data incrementally.

    format specifies the container format to use for the output. This can
    be FORMAT_XZ (default), FORMAT_ALONE, or FORMAT_RAW.

    check specifies the integrity check to use. For FORMAT_XZ, the default
    is CHECK_CRC64. FORMAT_ALONE and FORMAT_RAW do not suport integrity
    checks; for these formats, check must be omitted, or be CHECK_NONE.

    The settings used by the compressor can be specified either as a
    preset compression level (with the 'preset' argument), or in detail
    as a custom filter chain (with the 'filters' argument). For FORMAT_XZ
    and FORMAT_ALONE, the default is to use the PRESET_DEFAULT preset
    level. For FORMAT_RAW, the caller must always specify a filter chain;
    the raw compressor does not support preset compression levels.

    preset (if provided) should be an integer in the range 0-9, optionally
    OR-ed with the constant PRESET_EXTREME.

    filters (if provided) should be a sequence of dicts. Each dict should
    have an entry for "id" indicating the ID of the filter, plus
    additional entries for options to the filter.

    For one-shot compression, use the compress() function instead.
    """
    def __init__(self, format=FORMAT_XZ, check=-1, preset=None, filters=None):
        if format != FORMAT_XZ and check not in (-1, m.LZMA_CHECK_NONE):
            raise ValueError("Integrity...")
        if preset is not None and filters is not None:
            raise ValueError("Cannot...")
        if preset is None:
            preset = m.LZMA_PRESET_DEFAULT
        format = _parse_format(format)
        self.lock = threading.Lock()
        self.flushed = 0
        self.lzs = _new_lzma_stream()
        if format == FORMAT_XZ:
            if filters is None:
                if check == -1:
                    check = m.LZMA_CHECK_CRC64
                catch_lzma_error(m.lzma_easy_encoder, self.lzs,
                    preset, check)
            else:
                filters = parse_filter_chain_spec(filters)
                catch_lzma_error(m.lzma_stream_encoder, self.lzs,
                    filters, check)
        elif format == FORMAT_ALONE:
            if filters is None:
                options = ffi.new('lzma_options_lzma*')
                if m.lzma_lzma_preset(options, preset):
                    raise LZMAError("Invalid...")
                catch_lzma_error(m.lzma_alone_encoder, self.lzs,
                    options)
            else:
                raise NotImplementedError
        elif format == FORMAT_RAW:
            if filters is None:
                raise ValueError("Must...")
            filters = parse_filter_chain_spec(filters)
            catch_lzma_error(m.lzma_raw_encoder, self.lzs,
                filters)
        else:
            raise ValueError("Invalid...")

    def compress(self, data):
        """
        compress(data) -> bytes

        Provide data to the compressor object. Returns a chunk of
        compressed data if possible, or b"" otherwise.

        When you have finished providing data to the compressor, call the
        flush() method to finish the conversion process.
        """
        with self.lock:
            if self.flushed:
                raise ValueError("Compressor...")
            return self._compress(data)

    def _compress(self, data, action=m.LZMA_RUN):
        # TODO use realloc like in LZMADecompressor
        BUFSIZ = 8192

        lzs = self.lzs

        lzs.next_in = input_ = ffi.new('char[]', to_bytes(data))
        lzs.avail_in = len(data)
        outs = [ffi.new('char[]', BUFSIZ)]
        lzs.next_out, = outs
        lzs.avail_out = BUFSIZ

        siz = BUFSIZ

        while True:
            next_out_pos = int(ffi.cast('intptr_t', lzs.next_out))
            ret = catch_lzma_error(m.lzma_code, lzs, action)
            data_size = int(ffi.cast('intptr_t', lzs.next_out)) - next_out_pos
            if (action == m.LZMA_RUN and lzs.avail_in == 0) or \
                (action == m.LZMA_FINISH and ret == m.LZMA_STREAM_END):
                break
            elif lzs.avail_out == 0:
                # ran out of space in the output buffer
                #siz = (BUFSIZ << 1) + 6
                siz = 512
                outs.append(ffi.new('char[]', siz))
                lzs.next_out = outs[-1]
                lzs.avail_out = siz
        last_out = outs.pop()
        last_out_len = siz - lzs.avail_out
        last_out_piece = ffi.buffer(last_out[0:last_out_len], last_out_len)[:]

        return b''.join(ffi.buffer(nn)[:] for nn in outs) + last_out_piece

    def flush(self):
        with self.lock:
            if self.flushed:
                raise ValueError("Repeated...")
            self.flushed = 1
            return self._compress(b'', action=m.LZMA_FINISH)

    def __getstate__(self):
        raise TypeError("cannot serialize '%s' object" %
                        self.__class__.__name__)
        
