from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import unwrap_spec, WrappedDefault
from pypy.module._cffi_backend import ctypeobj, cdataobj


# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType, w_init=WrappedDefault(None))
def newp(space, ctype, w_init):
    return ctype.newp(w_init)

# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType)
def cast(space, ctype, w_ob):
    return ctype.cast(w_ob)

# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType)
def callback(space, ctype, w_callable, w_error=None):
    from pypy.module._cffi_backend.ccallback import W_CDataCallback
    return W_CDataCallback(space, ctype, w_callable, w_error)

# ____________________________________________________________

@unwrap_spec(cdata=cdataobj.W_CData)
def typeof(space, cdata):
    return cdata.ctype

# ____________________________________________________________

def sizeof(space, w_obj):
    ob = space.interpclass_w(w_obj)
    if isinstance(ob, cdataobj.W_CData):
        size = ob._sizeof()
    elif isinstance(ob, ctypeobj.W_CType):
        size = ob.size
        if size < 0:
            raise operationerrfmt(space.w_ValueError,
                                  "ctype '%s' is of unknown size",
                                  ob.name)
    else:
        raise OperationError(space.w_TypeError,
                            space.wrap("expected a 'cdata' or 'ctype' object"))
    return space.wrap(size)

@unwrap_spec(ctype=ctypeobj.W_CType)
def alignof(space, ctype):
    align = ctype.alignof()
    return space.wrap(align)

@unwrap_spec(ctype=ctypeobj.W_CType, fieldname="str_or_None")
def typeoffsetof(space, ctype, fieldname):
    ctype, offset = ctype.typeoffsetof(fieldname)
    return space.newtuple([space.wrap(ctype), space.wrap(offset)])

@unwrap_spec(ctype=ctypeobj.W_CType, cdata=cdataobj.W_CData, offset=int)
def rawaddressof(space, ctype, cdata, offset=0):
    return ctype.rawaddressof(cdata, offset)

# ____________________________________________________________

@unwrap_spec(ctype=ctypeobj.W_CType, replace_with=str)
def getcname(space, ctype, replace_with):
    p = ctype.name_position
    s = '%s%s%s' % (ctype.name[:p], replace_with, ctype.name[p:])
    return space.wrap(s)

# ____________________________________________________________

@unwrap_spec(cdata=cdataobj.W_CData, maxlen=int)
def string(space, cdata, maxlen=-1):
    return cdata.ctype.string(cdata, maxlen)

# ____________________________________________________________

def _get_types(space):
    return space.newtuple([space.gettypefor(cdataobj.W_CData),
                           space.gettypefor(ctypeobj.W_CType)])
