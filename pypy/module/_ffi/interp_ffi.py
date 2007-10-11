
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.libffi import CDLL, RTLD_LOCAL, RTLD_GLOBAL,\
     ffi_type_sint, ffi_type_double, ffi_type_slong
from pypy.rpython.lltypesystem import lltype, rffi

typemap = {
    'i' : ffi_type_sint,
    'l' : ffi_type_slong,
    'd' : ffi_type_double
}

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        self.cdll = CDLL(name)
        self.name = name
        self.w_cache = space.newdict()
        self.space = space

    def get_type(self, key):
        space = self.space
        try:
            return typemap[key]
        except KeyError:
            raise OperationError(space.w_ValueError, space.wrap(
                "Uknown type letter %s" % key))

    def ptr(self, space, name, w_argtypes, restype):
        """ Get a pointer for function name with provided argtypes
        and restype
        """
        w = space.wrap
        w_argtypes = space.newtuple(space.unpackiterable(w_argtypes))
        w_key = space.newtuple([w(name), w_argtypes, w(restype)])
        try:
            return space.getitem(self.w_cache, w_key)
        except OperationError, e:
            if e.match(space, space.w_KeyError):
                pass
            else:
                raise
        argtypes_w = space.unpackiterable(w_argtypes)
        argtypes = [space.str_w(w_arg) for w_arg in argtypes_w]
        ffi_argtypes = [self.get_type(arg) for arg in argtypes]
        ffi_restype = self.get_type(restype)
        try:
            ptr = self.cdll.getpointer(name, ffi_argtypes, ffi_restype)
            w_funcptr = W_FuncPtr(ptr, argtypes, restype)
            space.setitem(self.w_cache, w_key, w_funcptr)
            return w_funcptr
        except KeyError:
            raise OperationError(space.w_AttributeError, space.wrap(
                "No symbol %s found in library %s" % (name, self.name)))
    ptr.unwrap_spec = ['self', ObjSpace, str, W_Root, str]

def descr_new_cdll(space, w_type, name):
    try:
        return space.wrap(W_CDLL(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)
descr_new_cdll.unwrap_spec = [ObjSpace, W_Root, str]

W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    ptr         = interp2app(W_CDLL.ptr)
)

def push_arg(space, ptr, argtype, w_arg):
    if argtype == "i":
        ptr.push_arg(space.int_w(w_arg))
    elif argtype == "d":
        ptr.push_arg(space.float_w(w_arg))
    else:
        raise TypeError("Stuff changed in between?")

class W_FuncPtr(Wrappable):
    def __init__(self, ptr, argtypes, restype):
        self.ptr = ptr
        self.restype = restype
        self.argtypes = argtypes

    def call(self, space, arguments):
        args_w, kwds_w = arguments.unpack()
        # C has no keyword arguments
        if kwds_w:
            raise OperationError(space.w_TypeError, space.wrap(
                "Provided keyword arguments for C function call"))
        for argtype, w_arg in zip(self.argtypes, args_w):
            push_arg(space, self.ptr, argtype, w_arg)
        # a bit of specialcasing, rpython trick instead?
        if self.restype == "i":
            return space.wrap(self.ptr.call(rffi.INT))
        elif self.restype == "d":
            return space.wrap(self.ptr.call(rffi.DOUBLE))
        raise TypeError("Stuff changed in between?")
    call.unwrap_spec = ['self', ObjSpace, Arguments]

W_FuncPtr.typedef = TypeDef(
    'FuncPtr',
    __call__ = interp2app(W_FuncPtr.call)
)
