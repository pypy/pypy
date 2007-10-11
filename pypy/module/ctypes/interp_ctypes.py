
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.rlib.libffi import CDLL, RTLD_LOCAL, RTLD_GLOBAL,\
     ffi_type_sint
from pypy.rpython.lltypesystem import lltype, rffi

DEFAULT_MODE = RTLD_LOCAL

class W_CDLL(Wrappable):
    def __init__(self, name, mode):
        # XXX ignore mode for now
        self.cdll = CDLL(name)

class W_SimpleCData(Wrappable):
    pass

W_SimpleCData.typedef = TypeDef("_SimpleCData")

class W_CFuncPtr(Wrappable):
    def init(self, space, w_args):
        w_name_or_ordinal = space.getitem(w_args, space.wrap(0))
        w_cdll = space.getitem(w_args, space.wrap(1))
        handle = space.getattr(w_cdll, space.wrap('_handle'))
        self.space = space
        # XXX
        self.name = space.str_w(w_name_or_ordinal)
        self.handle = handle.cdll.getpointer(self.name, [], ffi_type_sint)
    init.unwrap_spec = ['self', ObjSpace, W_Root]

    def call(self, space):
        # NO ARGS
        return space.wrap(self.handle.call(rffi.INT))
    call.unwrap_spec = ['self', ObjSpace]

def descr_new_cfuncptr(space, w_subtype, w_args):
    return space.allocate_instance(W_CFuncPtr, w_subtype)
descr_new_cfuncptr.unwrap_spec = [ObjSpace, W_Root, W_Root]

def descr_name(space, w_obj):
    return space.wrap(space.type(w_obj).name)

def descr_set_name(space, w_obj, w_to):
    space.type(w_obj).name = space.str_w(w_to)

W_CFuncPtr.typedef = TypeDef("CFuncPtr",
     __new__ = interp2app(descr_new_cfuncptr),
     __init__ = interp2app(W_CFuncPtr.init),
     __name__ = GetSetProperty(descr_name, descr_set_name),
     __call__ = interp2app(W_CFuncPtr.call),
)

def dlopen(space, name, mode=DEFAULT_MODE):
    try:
        return space.wrap(W_CDLL(name, mode))
    except OSError, e:
        raise wrap_oserror(space, e)
dlopen.unwrap_spec = [ObjSpace, str, int]

# no public fields here
W_CDLL.typedef = TypeDef("_CDLL")

    
