
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.libffi import *
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.unroll import unrolling_iterable

TYPEMAP = {
    # XXX A mess with unsigned/signed/normal chars :-/
    'c' : ffi_type_uchar,
    'b' : ffi_type_schar,
    'B' : ffi_type_uchar,
    'h' : ffi_type_sshort,
    'H' : ffi_type_ushort,
    'i' : ffi_type_sint,
    'I' : ffi_type_uint,
    'l' : ffi_type_slong,
    'L' : ffi_type_ulong,
    # XXX I'm not sure what is long long here, let's assume it's 64 bit :-/
    'q' : ffi_type_sint64,
    'Q' : ffi_type_uint64,
    'f' : ffi_type_float,
    'd' : ffi_type_double,
    's' : ffi_type_pointer,
    'P' : ffi_type_pointer,
}

LL_TYPEMAP = {
    'c' : rffi.CHAR,
    'b' : rffi.UCHAR,
    'B' : rffi.CHAR,
    'h' : rffi.SHORT,
    'H' : rffi.USHORT,
    'i' : rffi.INT,
    'I' : rffi.UINT,
    'l' : rffi.LONG,
    'L' : rffi.ULONG,
    'q' : rffi.LONGLONG,
    'Q' : rffi.ULONGLONG,
    'f' : rffi.FLOAT,
    'd' : rffi.DOUBLE,
    's' : rffi.CCHARP,
    'P' : rffi.VOIDP,    
}

def _get_type(space, key):
    try:
        return TYPEMAP[key]
    except KeyError:
        raise OperationError(space.w_ValueError, space.wrap(
            "Uknown type letter %s" % key))
_get_type.unwrap_spec = [ObjSpace, str]

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        self.cdll = CDLL(name)
        self.name = name
        self.w_cache = space.newdict()
        self.space = space

    def get_type(self, key):
        space = self.space
        return _get_type(space, key)

    def ptr(self, space, name, w_argtypes, w_restype):
        """ Get a pointer for function name with provided argtypes
        and restype
        """
        if space.is_w(w_restype, space.w_None):
            restype = 'v'
            ffi_restype = ffi_type_void
        else:
            restype = space.str_w(w_restype)
            ffi_restype = self.get_type(restype)
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
        try:
            ptr = self.cdll.getpointer(name, ffi_argtypes, ffi_restype)
            w_funcptr = W_FuncPtr(ptr, argtypes, restype)
            space.setitem(self.w_cache, w_key, w_funcptr)
            return w_funcptr
        except KeyError:
            raise OperationError(space.w_AttributeError, space.wrap(
                "No symbol %s found in library %s" % (name, self.name)))
    ptr.unwrap_spec = ['self', ObjSpace, str, W_Root, W_Root]

def descr_new_cdll(space, w_type, name):
    try:
        return space.wrap(W_CDLL(space, name))
    except OSError, e:
        raise wrap_oserror(space, e)
descr_new_cdll.unwrap_spec = [ObjSpace, W_Root, str]

W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    ptr         = interp2app(W_CDLL.ptr),
    __doc__     = """ C Dynamically loaded library
use CDLL(libname) to create handle to C library (argument is processed the
same way as dlopen processes it). On such library call:
lib.ptr(func_name, argtype_list, restype)

where argtype_list is a list of single characters and restype is a single
character. Character meanings are more or less the same as in struct module,
except that s has trailing \x00 added, while p is considered a raw buffer.
"""
)

def pack_pointer(space, add_arg, argdesc, w_arg, push_func):
    arg = space.str_w(w_arg)
    ll_str = lltype.malloc(rffi.CCHARP.TO, len(arg), flavor='raw')
    for i in range(len(arg)):
        ll_str[i] = arg[i]
    push_func(add_arg, argdesc, ll_str)
    return ll_str

def unwrap_value(space, push_func, add_arg, argdesc, tp, w_arg, to_free):
    w = space.wrap
    # XXX how to handle LONGLONG here?
    # they're probably long, so we'll not get them through int_w
    if tp == "d" or tp == "f":
        push_func(add_arg, argdesc, space.float_w(w_arg))
    elif tp == "s":
        ll_str = rffi.str2charp(space.str_w(w_arg))
        if to_free is not None:
            to_free.append(ll_str)
        push_func(add_arg, argdesc, ll_str)
    elif tp == "P":
        # check for NULL ptr
        if space.is_w(w_arg, space.w_None):
            push_func(add_arg, argdesc, lltype.nullptr(rffi.VOIDP.TO))
        elif space.is_true(space.isinstance(w_arg, space.w_basestring)):
            if to_free is not None:
                to_free.append(pack_pointer(space, add_arg, argdesc, w_arg, push_func))
        else:
            mod = space.getbuiltinmodule('_ffi')
            w_StructureInstance = space.getattr(mod, w('StructureInstance'))
            w_ArrayInstance = space.getattr(mod, w('ArrayInstance'))
            if space.is_true(space.isinstance(w_arg, w_StructureInstance)) or\
                   space.is_true(space.isinstance(w_arg, w_ArrayInstance)):
                ptr = rffi.cast(rffi.VOIDP, space.int_w(space.getattr(w_arg, w('buffer'))))
                push_func(add_arg, argdesc, ptr)
            else:
                raise OperationError(space.w_TypeError, w(
                    "Expected structure, array or simple type"))
    elif tp == "c" or tp == "b" or tp == "B":
        s = space.str_w(w_arg)
        if len(s) != 1:
            raise OperationError(space.w_ValueError, w(
                "Expected string of length one as character"))
        s = s[0]
        push_func(add_arg, argdesc, s)
    else:
        #assert tp  "iIhHlLqQ"
        push_func(add_arg, argdesc, space.int_w(w_arg))
unwrap_value._annspecialcase_ = 'specialize:arg(1)'

ll_typemap_iter = unrolling_iterable(LL_TYPEMAP.items())

def wrap_value(space, func, add_arg, argdesc, tp):
    for c, ll_type in ll_typemap_iter:
        if tp == c:
            if c == 's':
                ptr = func(add_arg, argdesc, rffi.CCHARP)
                if not ptr:
                    return space.w_None
                return space.wrap(rffi.charp2str(ptr))
            elif c == 'P':
                res = func(add_arg, argdesc, rffi.VOIDP)
                if not res:
                    return space.w_None
                return space.wrap(rffi.cast(rffi.INT, res))
            #elif c == 'q' or c == 'Q' or c == 'L':
            #    return space.newlong(func(arg, ll_type))
            elif c == 'f' or c == 'd':
                return space.wrap(float(func(add_arg, argdesc, ll_type)))
            elif c == 'c' or c == 'b' or c == 'B':
                return space.wrap(chr(rffi.cast(rffi.INT, func(add_arg, argdesc,
                                                               ll_type))))
            elif c == 'h' or c == 'H':
                return space.wrap(rffi.cast(rffi.INT, func(add_arg, argdesc,
                                                           ll_type)))
            else:
                return space.wrap(intmask(func(add_arg, argdesc, ll_type)))
    return space.w_None
wrap_value._annspecialcase_ = 'specialize:arg(1)'

def ptr_call(ptr, some_arg, ll_type):
    return ptr.call(ll_type)
ptr_call._annspecialcase_ = 'specialize:arg(2)'

def push(ptr, argdesc, value):
    ptr.push_arg(value)
push._annspecialcase_ = 'specialize:argtype(2)'

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
        to_free = []
        i = 0
        for i in range(len(self.argtypes)):
            argtype = self.argtypes[i]
            w_arg = args_w[i]
            unwrap_value(space, push, self.ptr, i, argtype, w_arg, to_free)
            i += 1
        try:
            if self.restype != 'v':
                return wrap_value(space, ptr_call, self.ptr, None, self.restype)
            return space.w_None
        finally:
            for elem in to_free:
                lltype.free(elem, flavor='raw')
    call.unwrap_spec = ['self', ObjSpace, Arguments]

W_FuncPtr.typedef = TypeDef(
    'FuncPtr',
    __call__ = interp2app(W_FuncPtr.call)
)
