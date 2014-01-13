import weakref
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec
from pypy.module._cffi_backend import ctypeobj, ctypeptr, cdataobj
from pypy.module._weakref.interp__weakref import dead_ref
from rpython.rtyper.lltypesystem import lltype, rffi


def reduced_value(s):
    while True:
        divide = s & 1
        s >>= 1
        if not divide:
            return s

# ____________________________________________________________


class CffiHandles:
    def __init__(self, space):
        self.handles = []
        self.look_distance = 0

    def reserve_next_handle_index(self):
        # The reservation ordering done here is tweaked for pypy's
        # memory allocator.  We look from index 'look_distance'.
        # Look_distance increases from 0.  But we also look at
        # "look_distance/2" or "/4" or "/8", etc.  If we find that one
        # of these secondary locations is free, we assume it's because
        # there was recently a minor collection; so we reset
        # look_distance to 0 and start again from the lowest locations.
        length = len(self.handles)
        for d in range(self.look_distance, length):
            if self.handles[d]() is None:
                self.look_distance = d + 1
                return d
            s = reduced_value(d)
            if self.handles[s]() is None:
                break
        # restart from the beginning
        for d in range(0, length):
            if self.handles[d]() is None:
                self.look_distance = d + 1
                return d
        # full! extend, but don't use '+=' here
        self.handles = self.handles + [dead_ref] * (length // 3 + 5)
        self.look_distance = length + 1
        return length

    def store_handle(self, index, content):
        self.handles[index] = weakref.ref(content)

    def fetch_handle(self, index):
        if 0 <= index < len(self.handles):
            return self.handles[index]()
        return None

def get(space):
    return space.fromcache(CffiHandles)

# ____________________________________________________________

@unwrap_spec(w_ctype=ctypeobj.W_CType)
def newp_handle(space, w_ctype, w_x):
    if (not isinstance(w_ctype, ctypeptr.W_CTypePointer) or
        not w_ctype.is_void_ptr):
        raise operationerrfmt(space.w_TypeError,
                              "needs 'void *', got '%s'", w_ctype.name)
    index = get(space).reserve_next_handle_index()
    _cdata = rffi.cast(rffi.CCHARP, index + 1)
    new_cdataobj = cdataobj.W_CDataHandle(space, _cdata, w_ctype, w_x)
    get(space).store_handle(index, new_cdataobj)
    return new_cdataobj

@unwrap_spec(w_cdata=cdataobj.W_CData)
def from_handle(space, w_cdata):
    ctype = w_cdata.ctype
    if (not isinstance(ctype, ctypeptr.W_CTypePtrOrArray) or
        not ctype.can_cast_anything):
        raise operationerrfmt(space.w_TypeError,
                              "expected a 'cdata' object with a 'void *' out "
                              "of new_handle(), got '%s'", ctype.name)
    index = rffi.cast(lltype.Signed, w_cdata._cdata)
    original_cdataobj = get(space).fetch_handle(index - 1)
    #
    if isinstance(original_cdataobj, cdataobj.W_CDataHandle):
        return original_cdataobj.w_keepalive
    else:
        if index == 0:
            msg = "cannot use from_handle() on NULL pointer"
        else:
            msg = "'void *' value does not correspond to any object"
        raise OperationError(space.w_RuntimeError, space.wrap(msg))
