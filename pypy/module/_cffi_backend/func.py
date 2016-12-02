from rpython.rtyper.annlowlevel import llstr
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem.rstr import copy_string_to_raw
from rpython.rlib.objectmodel import keepalive_until_here, we_are_translated
from rpython.rlib import jit

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from pypy.module._cffi_backend import ctypeobj, cdataobj, allocator


# ____________________________________________________________

@unwrap_spec(w_ctype=ctypeobj.W_CType, w_init=WrappedDefault(None))
def newp(space, w_ctype, w_init):
    return w_ctype.newp(w_init, allocator.default_allocator)

# ____________________________________________________________

@unwrap_spec(w_ctype=ctypeobj.W_CType)
def cast(space, w_ctype, w_ob):
    return w_ctype.cast(w_ob)

# ____________________________________________________________

@unwrap_spec(w_ctype=ctypeobj.W_CType)
def callback(space, w_ctype, w_callable, w_error=None, w_onerror=None):
    from pypy.module._cffi_backend.ccallback import make_callback
    return make_callback(space, w_ctype, w_callable, w_error, w_onerror)

# ____________________________________________________________

@unwrap_spec(w_cdata=cdataobj.W_CData)
def typeof(space, w_cdata):
    return w_cdata.ctype

# ____________________________________________________________

def sizeof(space, w_obj):
    if isinstance(w_obj, cdataobj.W_CData):
        size = w_obj._sizeof()
    elif isinstance(w_obj, ctypeobj.W_CType):
        size = w_obj.size
        if size < 0:
            raise oefmt(space.w_ValueError,
                        "ctype '%s' is of unknown size", w_obj.name)
    else:
        raise oefmt(space.w_TypeError, "expected a 'cdata' or 'ctype' object")
    return space.newint(size)

@unwrap_spec(w_ctype=ctypeobj.W_CType)
def alignof(space, w_ctype):
    align = w_ctype.alignof()
    return space.newint(align)

@unwrap_spec(w_ctype=ctypeobj.W_CType, following=int)
def typeoffsetof(space, w_ctype, w_field_or_index, following=0):
    ctype, offset = w_ctype.direct_typeoffsetof(w_field_or_index, following)
    return space.newtuple([ctype, space.newint(offset)])

@unwrap_spec(w_ctype=ctypeobj.W_CType, w_cdata=cdataobj.W_CData, offset=int)
def rawaddressof(space, w_ctype, w_cdata, offset):
    return w_ctype.rawaddressof(w_cdata, offset)

# ____________________________________________________________

@unwrap_spec(w_ctype=ctypeobj.W_CType, replace_with=str)
def getcname(space, w_ctype, replace_with):
    p = w_ctype.name_position
    s = '%s%s%s' % (w_ctype.name[:p], replace_with, w_ctype.name[p:])
    return space.newtext(s)

# ____________________________________________________________

@unwrap_spec(w_cdata=cdataobj.W_CData, maxlen=int)
def string(space, w_cdata, maxlen=-1):
    return w_cdata.ctype.string(w_cdata, maxlen)

# ____________________________________________________________

@unwrap_spec(w_cdata=cdataobj.W_CData, length=int)
def unpack(space, w_cdata, length):
    return w_cdata.unpack(length)

# ____________________________________________________________

def _get_types(space):
    return space.newtuple([space.gettypefor(cdataobj.W_CData),
                           space.gettypefor(ctypeobj.W_CType)])

# ____________________________________________________________

def _get_common_types(space, w_dict):
    from pypy.module._cffi_backend.parse_c_type import ll_enum_common_types
    index = 0
    while True:
        p = ll_enum_common_types(rffi.cast(rffi.INT, index))
        if not p:
            break
        key = rffi.charp2str(p)
        value = rffi.charp2str(rffi.ptradd(p, len(key) + 1))
        space.setitem_str(w_dict, key, space.newtext(value))
        index += 1

# ____________________________________________________________

def _fetch_as_read_buffer(space, w_x):
    # xxx do we really need to implement the same mess as in CPython 2.7
    # w.r.t. buffers and memoryviews??
    try:
        buf = space.readbuf_w(w_x)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
        buf = space.buffer_w(w_x, space.BUF_SIMPLE)
    return buf

def _fetch_as_write_buffer(space, w_x):
    try:
        buf = space.writebuf_w(w_x)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
        buf = space.buffer_w(w_x, space.BUF_WRITABLE)
    return buf

@unwrap_spec(w_ctype=ctypeobj.W_CType)
def from_buffer(space, w_ctype, w_x):
    from pypy.module._cffi_backend import ctypearray, ctypeprim
    #
    if (not isinstance(w_ctype, ctypearray.W_CTypeArray) or
        not isinstance(w_ctype.ctptr.ctitem, ctypeprim.W_CTypePrimitiveChar)):
        raise oefmt(space.w_TypeError,
                    "needs 'char[]', got '%s'", w_ctype.name)
    #
    return _from_buffer(space, w_ctype, w_x)

def _from_buffer(space, w_ctype, w_x):
    buf = _fetch_as_read_buffer(space, w_x)
    if space.isinstance_w(w_x, space.w_bytes):
        _cdata = get_raw_address_of_string(space, w_x)
    else:
        try:
            _cdata = buf.get_raw_address()
        except ValueError:
            raise oefmt(space.w_TypeError,
                        "from_buffer() got a '%T' object, which supports the "
                        "buffer interface but cannot be rendered as a plain "
                        "raw address on PyPy", w_x)
    #
    return cdataobj.W_CDataFromBuffer(space, _cdata, w_ctype, buf, w_x)

# ____________________________________________________________

class RawBytes(object):
    def __init__(self, string):
        self.ptr = rffi.str2charp(string, track_allocation=False)
    def __del__(self):
        rffi.free_charp(self.ptr, track_allocation=False)

class RawBytesCache(object):
    def __init__(self, space):
        from pypy.interpreter.baseobjspace import W_Root
        from rpython.rlib import rweakref
        self.wdict = rweakref.RWeakKeyDictionary(W_Root, RawBytes)

@jit.dont_look_inside
def get_raw_address_of_string(space, w_x):
    """Special case for ffi.from_buffer(string).  Returns a 'char *' that
    is valid as long as the string object is alive.  Two calls to
    ffi.from_buffer(same_string) are guaranteed to return the same pointer.
    """
    from rpython.rtyper.annlowlevel import llstr
    from rpython.rtyper.lltypesystem.rstr import STR
    from rpython.rtyper.lltypesystem import llmemory
    from rpython.rlib import rgc

    cache = space.fromcache(RawBytesCache)
    rawbytes = cache.wdict.get(w_x)
    if rawbytes is None:
        data = space.bytes_w(w_x)
        if we_are_translated() and not rgc.can_move(data):
            lldata = llstr(data)
            data_start = (llmemory.cast_ptr_to_adr(lldata) +
                          rffi.offsetof(STR, 'chars') +
                          llmemory.itemoffsetof(STR.chars, 0))
            data_start = rffi.cast(rffi.CCHARP, data_start)
            data_start[len(data)] = '\x00'   # write the final extra null
            return data_start
        rawbytes = RawBytes(data)
        cache.wdict.set(w_x, rawbytes)
    return rawbytes.ptr

# ____________________________________________________________


def unsafe_escaping_ptr_for_ptr_or_array(w_cdata):
    if not w_cdata.ctype.is_nonfunc_pointer_or_array:
        raise oefmt(w_cdata.space.w_TypeError,
                    "expected a pointer or array ctype, got '%s'",
                    w_cdata.ctype.name)
    return w_cdata.unsafe_escaping_ptr()

c_memmove = rffi.llexternal('memmove', [rffi.CCHARP, rffi.CCHARP,
                                        rffi.SIZE_T], lltype.Void,
                                _nowrapper=True)

@unwrap_spec(n=int)
def memmove(space, w_dest, w_src, n):
    if n < 0:
        raise oefmt(space.w_ValueError, "negative size")

    # cases...
    src_buf = None
    src_data = lltype.nullptr(rffi.CCHARP.TO)
    if isinstance(w_src, cdataobj.W_CData):
        src_data = unsafe_escaping_ptr_for_ptr_or_array(w_src)
        src_is_ptr = True
    else:
        src_buf = _fetch_as_read_buffer(space, w_src)
        try:
            src_data = src_buf.get_raw_address()
            src_is_ptr = True
        except ValueError:
            src_is_ptr = False

    if src_is_ptr:
        src_string = None
    else:
        if n == src_buf.getlength():
            src_string = src_buf.as_str()
        else:
            src_string = src_buf.getslice(0, n, 1, n)

    dest_buf = None
    dest_data = lltype.nullptr(rffi.CCHARP.TO)
    if isinstance(w_dest, cdataobj.W_CData):
        dest_data = unsafe_escaping_ptr_for_ptr_or_array(w_dest)
        dest_is_ptr = True
    else:
        dest_buf = _fetch_as_write_buffer(space, w_dest)
        try:
            dest_data = dest_buf.get_raw_address()
            dest_is_ptr = True
        except ValueError:
            dest_is_ptr = False

    if dest_is_ptr:
        if src_is_ptr:
            c_memmove(dest_data, src_data, rffi.cast(rffi.SIZE_T, n))
        else:
            copy_string_to_raw(llstr(src_string), dest_data, 0, n)
    else:
        # nowadays this case should be rare or impossible: as far as
        # I know, all common types implementing the *writable* buffer
        # interface now support get_raw_address()
        if src_is_ptr:
            for i in range(n):
                dest_buf.setitem(i, src_data[i])
        else:
            for i in range(n):
                dest_buf.setitem(i, src_string[i])

    keepalive_until_here(src_buf)
    keepalive_until_here(dest_buf)
    keepalive_until_here(w_src)
    keepalive_until_here(w_dest)

# ____________________________________________________________

@unwrap_spec(w_cdata=cdataobj.W_CData)
def gcp(space, w_cdata, w_destructor):
    return w_cdata.with_gc(w_destructor)
