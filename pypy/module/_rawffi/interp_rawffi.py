import sys
from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, wrap_oserror, operationerrfmt
from pypy.interpreter.gateway import interp2app, NoneNotWrapped, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.clibffi import *
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.unroll import unrolling_iterable
import pypy.rlib.rposix as rposix

_MS_WINDOWS = os.name == "nt"

if _MS_WINDOWS:
    from pypy.rlib import rwin32

from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.rarithmetic import intmask, r_uint, r_singlefloat
from pypy.module._rawffi.tracker import tracker

TYPEMAP = {
    # XXX A mess with unsigned/signed/normal chars :-/
    'c' : ffi_type_uchar,
    'b' : ffi_type_schar,
    'B' : ffi_type_uchar,
    'h' : ffi_type_sshort,
    'u' : cast_type_to_ffitype(lltype.UniChar),
    'H' : ffi_type_ushort,
    'i' : cast_type_to_ffitype(rffi.INT),
    'I' : cast_type_to_ffitype(rffi.UINT),
    'l' : cast_type_to_ffitype(rffi.LONG),
    'L' : cast_type_to_ffitype(rffi.ULONG),
    'q' : cast_type_to_ffitype(rffi.LONGLONG),
    'Q' : cast_type_to_ffitype(rffi.ULONGLONG),
    'f' : ffi_type_float,
    'd' : ffi_type_double,
    'g' : ffi_type_longdouble,
    's' : ffi_type_pointer,
    'P' : ffi_type_pointer,
    'z' : ffi_type_pointer,
    'O' : ffi_type_pointer,
    'Z' : ffi_type_pointer,
    '?' : cast_type_to_ffitype(lltype.Bool),
}
TYPEMAP_PTR_LETTERS = "POszZ"
TYPEMAP_NUMBER_LETTERS = "bBhHiIlLqQ?"

if _MS_WINDOWS:
    TYPEMAP['X'] = ffi_type_pointer
    TYPEMAP['v'] = ffi_type_sshort
    TYPEMAP_PTR_LETTERS += 'X'
    TYPEMAP_NUMBER_LETTERS += 'v'

def size_alignment(ffi_type):
    return intmask(ffi_type.c_size), intmask(ffi_type.c_alignment)

LL_TYPEMAP = {
    'c' : rffi.CHAR,
    'u' : lltype.UniChar,
    'b' : rffi.SIGNEDCHAR,
    'B' : rffi.UCHAR,
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
    'g' : rffi.LONGDOUBLE,
    's' : rffi.CCHARP,
    'z' : rffi.CCHARP,
    'Z' : rffi.CArrayPtr(lltype.UniChar),
    'O' : rffi.VOIDP,
    'P' : rffi.VOIDP,
    '?' : lltype.Bool,
}

if _MS_WINDOWS:
    LL_TYPEMAP['X'] = rffi.CCHARP
    LL_TYPEMAP['v'] = rffi.SHORT

def letter2tp(space, key):
    from pypy.module._rawffi.array import PRIMITIVE_ARRAY_TYPES
    try:
        return PRIMITIVE_ARRAY_TYPES[key]
    except KeyError:
        raise operationerrfmt(space.w_ValueError,
                              "Unknown type letter %s", key)

def unpack_simple_shape(space, w_shape):
    # 'w_shape' must be either a letter or a tuple (struct, 1).
    if space.is_true(space.isinstance(w_shape, space.w_str)):
        letter = space.str_w(w_shape)
        return letter2tp(space, letter)
    else:
        w_shapetype, w_length = space.fixedview(w_shape, expected_length=2)
        from pypy.module._rawffi.structure import W_Structure
        return space.interp_w(W_Structure, w_shapetype)

def unpack_shape_with_length(space, w_shape):
    # Allow 'w_shape' to be a letter or any (shape, number).
    # The result is always a W_Array.
    if space.is_true(space.isinstance(w_shape, space.w_str)):
        letter = space.str_w(w_shape)
        return letter2tp(space, letter)
    else:
        w_shapetype, w_length = space.fixedview(w_shape, expected_length=2)
        length = space.int_w(w_length)
        shape = space.interp_w(W_DataShape, w_shapetype)
        if shape._array_shapes is None:
            shape._array_shapes = {}
        try:
            result = shape._array_shapes[length]
        except KeyError:
            from pypy.module._rawffi.array import W_Array
            if isinstance(shape, W_Array) and length == 1:
                result = shape
            else:
                ffitype = shape.get_basic_ffi_type()
                size = shape.size * length
                result = W_Array(ffitype, size)
            shape._array_shapes[length] = result
        return result

def unpack_resshape(space, w_restype):
    if space.is_w(w_restype, space.w_None):
        return None
    return unpack_simple_shape(space, w_restype)

def unpack_argshapes(space, w_argtypes):
    return [unpack_simple_shape(space, w_arg)
            for w_arg in space.unpackiterable(w_argtypes)]

class W_CDLL(Wrappable):
    def __init__(self, space, name, cdll):
        self.cdll = cdll
        self.name = name
        self.w_cache = space.newdict()
        self.space = space

    @unwrap_spec(flags=int)
    def ptr(self, space, w_name, w_argtypes, w_restype, flags=FUNCFLAG_CDECL):
        """ Get a pointer for function name with provided argtypes
        and restype
        """
        resshape = unpack_resshape(space, w_restype)
        w = space.wrap
        argtypes_w = space.fixedview(w_argtypes)
        w_argtypes = space.newtuple(argtypes_w)
        w_key = space.newtuple([w_name, w_argtypes, w(resshape)])
        try:
            return space.getitem(self.w_cache, w_key)
        except OperationError, e:
            if e.match(space, space.w_KeyError):
                pass
            else:
                raise
        # Array arguments not supported directly (in C, an array argument
        # will be just a pointer).  And the result cannot be an array (at all).
        argshapes = unpack_argshapes(space, w_argtypes)
        ffi_argtypes = [shape.get_basic_ffi_type() for shape in argshapes]
        if resshape is not None:
            ffi_restype = resshape.get_basic_ffi_type()
        else:
            ffi_restype = ffi_type_void

        if space.is_true(space.isinstance(w_name, space.w_str)):
            name = space.str_w(w_name)

            try:
                ptr = self.cdll.getrawpointer(name, ffi_argtypes, ffi_restype,
                                              flags)
            except KeyError:
                raise operationerrfmt(space.w_AttributeError,
                    "No symbol %s found in library %s", name, self.name)
        
        elif (_MS_WINDOWS and
              space.is_true(space.isinstance(w_name, space.w_int))):
            ordinal = space.int_w(w_name)
            try:
                ptr = self.cdll.getrawpointer_byordinal(ordinal, ffi_argtypes,
                                                        ffi_restype, flags)
            except KeyError:
                raise operationerrfmt(space.w_AttributeError,
                    "No symbol %d found in library %s", ordinal, self.name)
        else:
            raise OperationError(space.w_TypeError, space.wrap(
                "function name must be string or integer"))

        w_funcptr = W_FuncPtr(space, ptr, argshapes, resshape)
        space.setitem(self.w_cache, w_key, w_funcptr)
        return w_funcptr

    @unwrap_spec(name=str)
    def getaddressindll(self, space, name):
        try:
            address_as_uint = rffi.cast(lltype.Unsigned,
                                        self.cdll.getaddressindll(name))
        except KeyError:
            raise operationerrfmt(space.w_ValueError,
                                  "Cannot find symbol %s", name)
        return space.wrap(address_as_uint)

@unwrap_spec(name='str_or_None')
def descr_new_cdll(space, w_type, name):
    try:
        cdll = CDLL(name)
    except DLOpenError, e:
        raise operationerrfmt(space.w_OSError, '%s: %s', name,
                              e.msg or 'unspecified error')
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(W_CDLL(space, name, cdll))

W_CDLL.typedef = TypeDef(
    'CDLL',
    __new__     = interp2app(descr_new_cdll),
    ptr         = interp2app(W_CDLL.ptr),
    getaddressindll = interp2app(W_CDLL.getaddressindll),
    __doc__     = """ C Dynamically loaded library
use CDLL(libname) to create a handle to a C library (the argument is processed
the same way as dlopen processes it). On such a library you can call:
lib.ptr(func_name, argtype_list, restype)

where argtype_list is a list of single characters and restype is a single
character. The character meanings are more or less the same as in the struct
module, except that s has trailing \x00 added, while p is considered a raw
buffer.""" # xxx fix doc
)

unroll_letters_for_numbers = unrolling_iterable(TYPEMAP_NUMBER_LETTERS)

def segfault_exception(space, reason):
    w_mod = space.getbuiltinmodule("_rawffi")
    w_exception = space.getattr(w_mod, space.wrap("SegfaultException"))
    return OperationError(w_exception, space.wrap(reason))

class W_DataShape(Wrappable):
    _array_shapes = None
    size = 0
    alignment = 0
    itemcode = '\0'

    def allocate(self, space, length, autofree=False):
        raise NotImplementedError

    def get_basic_ffi_type(self):
        raise NotImplementedError

    def descr_get_ffi_type(self, space):
        # XXX: this assumes that you have the _ffi module enabled. In the long
        # term, probably we will move the code for build structures and arrays
        # from _rawffi to _ffi
        from pypy.module._ffi.interp_ffi import W_FFIType
        return W_FFIType('<unknown>', self.get_basic_ffi_type(), self)

    @unwrap_spec(n=int)
    def descr_size_alignment(self, space, n=1):
        return space.newtuple([space.wrap(self.size * n),
                               space.wrap(self.alignment)])
    

class W_DataInstance(Wrappable):
    def __init__(self, space, size, address=r_uint(0)):
        if address:
            self.ll_buffer = rffi.cast(rffi.VOIDP, address)
        else:
            self.ll_buffer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw',
                                           zero=True)
            if tracker.DO_TRACING:
                ll_buf = rffi.cast(lltype.Signed, self.ll_buffer)
                tracker.trace_allocation(ll_buf, self)

    def getbuffer(self, space):
        return space.wrap(rffi.cast(lltype.Unsigned, self.ll_buffer))

    def byptr(self, space):
        from pypy.module._rawffi.array import ARRAY_OF_PTRS
        array = ARRAY_OF_PTRS.allocate(space, 1)
        array.setitem(space, 0, space.wrap(self))
        return space.wrap(array)

    def free(self, space):
        if not self.ll_buffer:
            raise segfault_exception(space, "freeing NULL pointer")
        self._free()

    def _free(self):
        if tracker.DO_TRACING:
            ll_buf = rffi.cast(lltype.Signed, self.ll_buffer)
            tracker.trace_free(ll_buf)
        lltype.free(self.ll_buffer, flavor='raw')
        self.ll_buffer = lltype.nullptr(rffi.VOIDP.TO)

    def descr_buffer(self, space):
        from pypy.module._rawffi.buffer import RawFFIBuffer
        return space.wrap(RawFFIBuffer(self))

    def getrawsize(self):
        raise NotImplementedError("abstract base class")

def unwrap_truncate_int(TP, space, w_arg):
    if space.is_true(space.isinstance(w_arg, space.w_int)):
        return rffi.cast(TP, space.int_w(w_arg))
    else:
        return rffi.cast(TP, space.bigint_w(w_arg).ulonglongmask())
unwrap_truncate_int._annspecialcase_ = 'specialize:arg(0)'

def unwrap_value(space, push_func, add_arg, argdesc, letter, w_arg):
    w = space.wrap
    if letter in TYPEMAP_PTR_LETTERS:
        # check for NULL ptr
        datainstance = space.interpclass_w(w_arg)
        if isinstance(datainstance, W_DataInstance):
            ptr = datainstance.ll_buffer
        else:
            ptr = unwrap_truncate_int(rffi.VOIDP, space, w_arg)
        push_func(add_arg, argdesc, ptr)
    elif letter == "d":
        push_func(add_arg, argdesc, space.float_w(w_arg))
    elif letter == "f":
        push_func(add_arg, argdesc, rffi.cast(rffi.FLOAT,
                                              space.float_w(w_arg)))
    elif letter == "g":
        push_func(add_arg, argdesc, rffi.cast(rffi.LONGDOUBLE,
                                              space.float_w(w_arg)))
    elif letter == "c":
        s = space.str_w(w_arg)
        if len(s) != 1:
            raise OperationError(space.w_TypeError, w(
                "Expected string of length one as character"))
        val = s[0]
        push_func(add_arg, argdesc, val)
    elif letter == 'u':
        s = space.unicode_w(w_arg)
        if len(s) != 1:
            raise OperationError(space.w_TypeError, w(
                "Expected unicode string of length one as wide character"))
        val = s[0]
        push_func(add_arg, argdesc, val)
    else:
        for c in unroll_letters_for_numbers:
            if letter == c:
                TP = LL_TYPEMAP[c]
                val = unwrap_truncate_int(TP, space, w_arg)
                push_func(add_arg, argdesc, val)
                return
        else:
            raise OperationError(space.w_TypeError,
                                 space.wrap("cannot directly write value"))
unwrap_value._annspecialcase_ = 'specialize:arg(1)'

ll_typemap_iter = unrolling_iterable(LL_TYPEMAP.items())

def wrap_value(space, func, add_arg, argdesc, letter):
    for c, ll_type in ll_typemap_iter:
        if letter == c:
            if c in TYPEMAP_PTR_LETTERS:
                res = func(add_arg, argdesc, rffi.VOIDP)
                return space.wrap(rffi.cast(lltype.Unsigned, res))
            elif c == 'q' or c == 'Q' or c == 'L' or c == 'c' or c == 'u':
                return space.wrap(func(add_arg, argdesc, ll_type))
            elif c == 'f' or c == 'd' or c == 'g':
                return space.wrap(float(func(add_arg, argdesc, ll_type)))
            else:
                return space.wrap(intmask(func(add_arg, argdesc, ll_type)))
    raise OperationError(space.w_TypeError,
                         space.wrap("cannot directly read value"))
wrap_value._annspecialcase_ = 'specialize:arg(1)'

class W_FuncPtr(Wrappable):
    def __init__(self, space, ptr, argshapes, resshape):
        self.ptr = ptr
        self.argshapes = argshapes
        self.resshape = resshape

    def getbuffer(self, space):
        return space.wrap(rffi.cast(lltype.Unsigned, self.ptr.funcsym))

    def byptr(self, space):
        from pypy.module._rawffi.array import ARRAY_OF_PTRS
        array = ARRAY_OF_PTRS.allocate(space, 1)
        array.setitem(space, 0, self.getbuffer(space))
        if tracker.DO_TRACING:
            # XXX this is needed, because functions tend to live forever
            #     hence our testing is not performing that well
            del tracker.alloced[rffi.cast(lltype.Signed, array.ll_buffer)]
        return space.wrap(array)

    def call(self, space, args_w):
        from pypy.module._rawffi.array import W_ArrayInstance
        from pypy.module._rawffi.structure import W_StructureInstance
        from pypy.module._rawffi.structure import W_Structure
        argnum = len(args_w)
        if argnum != len(self.argshapes):
            msg = "Wrong number of arguments: expected %d, got %d"
            raise operationerrfmt(space.w_TypeError, msg,
                                  len(self.argshapes), argnum)
        args_ll = []
        for i in range(argnum):
            argshape = self.argshapes[i]
            w_arg = args_w[i]
            if isinstance(argshape, W_Structure):   # argument by value
                arg = space.interp_w(W_StructureInstance, w_arg)
                xsize, xalignment = size_alignment(self.ptr.argtypes[i])
                if (arg.shape.size != xsize or
                    arg.shape.alignment != xalignment):
                    msg = ("Argument %d should be a structure of size %d and "
                           "alignment %d, "
                           "got instead size %d and alignment %d")
                    raise operationerrfmt(space.w_TypeError, msg, i+1,
                            xsize, xalignment, arg.shape.size,
                            arg.shape.alignment)
            else:
                arg = space.interp_w(W_ArrayInstance, w_arg)
                if arg.length != 1:
                    msg = ("Argument %d should be an array of length 1, "
                           "got length %d")
                    raise operationerrfmt(space.w_TypeError, msg,
                                          i+1, arg.length)
                argletter = argshape.itemcode
                letter = arg.shape.itemcode
                if letter != argletter:
                    if not (argletter in TYPEMAP_PTR_LETTERS and
                            letter in TYPEMAP_PTR_LETTERS):
                        msg = "Argument %d should be typecode %s, got %s"
                        raise operationerrfmt(space.w_TypeError, msg, 
                                              i+1, argletter, letter)
            args_ll.append(arg.ll_buffer)
            # XXX we could avoid the intermediate list args_ll

        try:
            if self.resshape is not None:
                result = self.resshape.allocate(space, 1, autofree=True)
                self.ptr.call(args_ll, result.ll_buffer)
                return space.wrap(result)
            else:
                self.ptr.call(args_ll, lltype.nullptr(rffi.VOIDP.TO))
                return space.w_None
        except StackCheckError, e:
            raise OperationError(space.w_ValueError, space.wrap(e.message))

@unwrap_spec(addr=r_uint, flags=int)
def descr_new_funcptr(space, w_tp, addr, w_args, w_res, flags=FUNCFLAG_CDECL):
    argshapes = unpack_argshapes(space, w_args)
    resshape = unpack_resshape(space, w_res)
    ffi_args = [shape.get_basic_ffi_type() for shape in argshapes]
    ffi_res = resshape.get_basic_ffi_type()
    ptr = RawFuncPtr('???', ffi_args, ffi_res, rffi.cast(rffi.VOIDP, addr),
                     flags)
    return space.wrap(W_FuncPtr(space, ptr, argshapes, resshape))

W_FuncPtr.typedef = TypeDef(
    'FuncPtr',
    __new__  = interp2app(descr_new_funcptr),
    __call__ = interp2app(W_FuncPtr.call),
    buffer   = GetSetProperty(W_FuncPtr.getbuffer),
    byptr    = interp2app(W_FuncPtr.byptr),
)
W_FuncPtr.typedef.acceptable_as_base_class = False

def _create_new_accessor(func_name, name):
    @unwrap_spec(tp_letter=str)
    def accessor(space, tp_letter):
        if len(tp_letter) != 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "Expecting string of length one"))
        tp_letter = tp_letter[0] # fool annotator
        try:
            return space.wrap(intmask(getattr(TYPEMAP[tp_letter], name)))
        except KeyError:
            raise operationerrfmt(space.w_ValueError,
                        "Unknown type specification %s", tp_letter)
    return func_with_new_name(accessor, func_name)

sizeof = _create_new_accessor('sizeof', 'c_size')
alignment = _create_new_accessor('alignment', 'c_alignment')

@unwrap_spec(address=r_uint, maxlength=int)
def charp2string(space, address, maxlength=sys.maxint):
    if address == 0:
        return space.w_None
    s = rffi.charp2strn(rffi.cast(rffi.CCHARP, address), maxlength)
    return space.wrap(s)

@unwrap_spec(address=r_uint, maxlength=int)
def wcharp2unicode(space, address, maxlength=sys.maxint):
    if address == 0:
        return space.w_None
    s = rffi.wcharp2unicoden(rffi.cast(rffi.CWCHARP, address), maxlength)
    return space.wrap(s)

@unwrap_spec(address=r_uint, maxlength=int)
def charp2rawstring(space, address, maxlength=-1):
    if maxlength == -1:
        return charp2string(space, address)
    s = rffi.charpsize2str(rffi.cast(rffi.CCHARP, address), maxlength)
    return space.wrap(s)

@unwrap_spec(address=r_uint, maxlength=int)
def wcharp2rawunicode(space, address, maxlength=-1):
    if maxlength == -1:
        return wcharp2unicode(space, address)
    s = rffi.wcharpsize2unicode(rffi.cast(rffi.CWCHARP, address), maxlength)
    return space.wrap(s)

if _MS_WINDOWS:
    @unwrap_spec(code=int)
    def FormatError(space, code):
        return space.wrap(rwin32.FormatError(code))

    @unwrap_spec(hresult=int)
    def check_HRESULT(space, hresult):
        if rwin32.FAILED(hresult):
            raise OperationError(space.w_WindowsError, space.wrap(hresult))
        return space.wrap(hresult)

def get_libc(space):
    name = get_libc_name()
    try:
        cdll = CDLL(name)
    except OSError, e:
        raise wrap_oserror(space, e)
    return space.wrap(W_CDLL(space, name, cdll))

def get_errno(space):
    return space.wrap(rposix.get_errno())

def set_errno(space, w_errno):
    rposix.set_errno(space.int_w(w_errno))

def get_last_error(space):
    from pypy.rlib.rwin32 import GetLastError
    return space.wrap(GetLastError())

def set_last_error(space, w_error):
    from pypy.rlib.rwin32 import SetLastError
    SetLastError(space.uint_w(w_error))
