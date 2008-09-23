import sys
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app, NoneNotWrapped
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.libffi import *
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.unroll import unrolling_iterable

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
    'u' : ffi_type_uint, # XXX think deeper how to map it properly
    'H' : ffi_type_ushort,
    'i' : cast_type_to_ffitype(rffi.INT),
    'I' : cast_type_to_ffitype(rffi.UINT),
    'l' : cast_type_to_ffitype(rffi.LONG),
    'L' : cast_type_to_ffitype(rffi.ULONG),
    'q' : cast_type_to_ffitype(rffi.LONGLONG),
    'Q' : cast_type_to_ffitype(rffi.ULONGLONG),
    'f' : ffi_type_float,
    'd' : ffi_type_double,
    's' : ffi_type_pointer,
    'P' : ffi_type_pointer,
    'z' : ffi_type_pointer,
    'O' : ffi_type_pointer,
    'Z' : ffi_type_pointer,
}
TYPEMAP_PTR_LETTERS = "POszZ"

def size_alignment(ffi_type):
    return intmask(ffi_type.c_size), intmask(ffi_type.c_alignment)

UNPACKED_TYPECODES = dict([(code, (code,) + size_alignment(field_desc))
                           for code, field_desc in TYPEMAP.items()])

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
    's' : rffi.CCHARP,
    'z' : rffi.CCHARP,
    'Z' : rffi.CArrayPtr(lltype.UniChar),
    'O' : rffi.VOIDP,
    'P' : rffi.VOIDP,
    'v' : lltype.Void,
}

def letter2tp(space, key):
    try:
        return UNPACKED_TYPECODES[key]
    except KeyError:
        raise OperationError(space.w_ValueError, space.wrap(
            "Unknown type letter %s" % (key,)))

def _get_type_(space, key):
    try:
        return TYPEMAP[key]
    except KeyError:
        raise OperationError(space.w_ValueError, space.wrap(
            "Unknown type letter %s" % (key,)))
    
def unpack_to_ffi_type(space, w_shape, allow_void=False, shape=False):
    resshape = None
    if space.is_true(space.isinstance(w_shape, space.w_str)):
        letter = space.str_w(w_shape)
        if allow_void and letter == 'v':
            return 'v', ffi_type_void, None
        ffi_type = _get_type_(space, letter)
        if shape:
            from pypy.module._rawffi.array import get_array_cache
            cache = get_array_cache(space)
            resshape = cache.get_array_type(letter2tp(space, letter))
    else:
        letter = 'V'
        w_shapetype, w_length = space.viewiterable(w_shape, expected_length=2)
        from pypy.module._rawffi.structure import W_Structure
        resshape = space.interp_w(W_Structure, w_shapetype)
        ffi_type = resshape.get_ffi_type()
    return letter, ffi_type, resshape

def unpack_to_size_alignment(space, w_shape):
    if space.is_true(space.isinstance(w_shape, space.w_str)):
        letter = space.str_w(w_shape)
        return letter2tp(space, letter)
    else:
        w_shapetype, w_length = space.viewiterable(w_shape, expected_length=2)
        resshape = space.interp_w(W_DataShape, w_shapetype)
        length = space.int_w(w_length)
        size, alignment = resshape._size_alignment()
        return ('V', length*size, alignment) # value object

def unpack_resshape(space, w_restype):
    if space.is_w(w_restype, space.w_None):
        resshape = None
        ffi_restype = ffi_type_void
    else:
        tp_letter, ffi_restype, resshape = unpack_to_ffi_type(space,
                                                    w_restype,
                                                    allow_void=True,
                                                    shape=True)
    return ffi_restype, resshape

def unpack_argshapes(space, w_argtypes):
    argletters = []
    ffi_argtypes = []
    for w_arg in space.unpackiterable(w_argtypes):
        argletter, ffi_argtype, _ = unpack_to_ffi_type(space, w_arg)
        argletters.append(argletter)
        ffi_argtypes.append(ffi_argtype)
    return ffi_argtypes, argletters

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        self.cdll = CDLL(name)
        self.name = name
        self.w_cache = space.newdict()
        self.space = space

    def ptr(self, space, name, w_argtypes, w_restype):
        """ Get a pointer for function name with provided argtypes
        and restype
        """
        ffi_restype, resshape = unpack_resshape(space, w_restype)
        w = space.wrap
        argtypes_w = space.viewiterable(w_argtypes)
        w_argtypes = space.newtuple(argtypes_w)
        w_key = space.newtuple([w(name), w_argtypes, w(resshape)])
        try:
            return space.getitem(self.w_cache, w_key)
        except OperationError, e:
            if e.match(space, space.w_KeyError):
                pass
            else:
                raise
        ffi_argtypes, argletters = unpack_argshapes(space, w_argtypes)
        try:
            ptr = self.cdll.getrawpointer(name, ffi_argtypes, ffi_restype)
            w_funcptr = W_FuncPtr(space, ptr, argletters, resshape)
            space.setitem(self.w_cache, w_key, w_funcptr)
            return w_funcptr
        except KeyError:
            raise OperationError(space.w_AttributeError, space.wrap(
                "No symbol %s found in library %s" % (name, self.name)))
    ptr.unwrap_spec = ['self', ObjSpace, str, W_Root, W_Root]

    def getaddressindll(self, space, name):
        try:
            address_as_uint = rffi.cast(lltype.Unsigned,
                                        self.cdll.getaddressindll(name))
        except KeyError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("Cannot find symbol %s" % (name,)))
        return space.wrap(address_as_uint)
    getaddressindll.unwrap_spec = ['self', ObjSpace, str]

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

unroll_letters_for_numbers = unrolling_iterable("bBhHiIlLqQ")

def segfault_exception(space, reason):
    w_mod = space.getbuiltinmodule("_rawffi")
    w_exception = space.getattr(w_mod, space.wrap("SegfaultException"))
    return OperationError(w_exception, space.wrap(reason))

class W_DataShape(Wrappable):
    
    def allocate(self, space, length, autofree=False):
        raise NotImplementedError

    def _size_alignment(self):
        raise NotImplementedError
    
    def descr_size_alignment(self, space, n=1):
        size, alignment = self._size_alignment()
        return space.newtuple([space.wrap(size * n),
                               space.wrap(alignment)])
    descr_size_alignment.unwrap_spec = ['self', ObjSpace, int]
    

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

    def getbuffer(space, self):
        return space.wrap(rffi.cast(lltype.Unsigned, self.ll_buffer))

    def byptr(self, space):
        from pypy.module._rawffi.array import get_array_cache
        array_of_ptr = get_array_cache(space).array_of_ptr
        array = array_of_ptr.allocate(space, 1)
        array.setitem(space, 0, space.wrap(self))
        return space.wrap(array)
    byptr.unwrap_spec = ['self', ObjSpace]

    def free(self, space):
        if not self.ll_buffer:
            raise segfault_exception(space, "freeing NULL pointer")
        self._free()
    free.unwrap_spec = ['self', ObjSpace]

    def _free(self):
        if tracker.DO_TRACING:
            ll_buf = rffi.cast(lltype.Signed, self.ll_buffer)
            tracker.trace_free(ll_buf)
        lltype.free(self.ll_buffer, flavor='raw')
        self.ll_buffer = lltype.nullptr(rffi.VOIDP.TO)

    def descr_buffer(self, space):
        from pypy.module._rawffi.buffer import RawFFIBuffer
        return space.wrap(RawFFIBuffer(self))
    descr_buffer.unwrap_spec = ['self', ObjSpace]

    def getrawsize(self):
        raise NotImplementedError("abstract base class")

def unwrap_truncate_int(TP, space, w_arg):
    if space.is_true(space.isinstance(w_arg, space.w_int)):
        return rffi.cast(TP, space.int_w(w_arg))
    else:
        return rffi.cast(TP, space.bigint_w(w_arg).ulonglongmask())
unwrap_truncate_int._annspecialcase_ = 'specialize:arg(0)'

def unwrap_value(space, push_func, add_arg, argdesc, tp, w_arg):
    letter, _, _ = tp
    w = space.wrap
    if letter == "d":
        push_func(add_arg, argdesc, space.float_w(w_arg))
    elif letter == "f":
        push_func(add_arg, argdesc, rffi.cast(rffi.FLOAT,
                                              space.float_w(w_arg)))
    elif letter in TYPEMAP_PTR_LETTERS:
        # check for NULL ptr
        datainstance = space.interpclass_w(w_arg)
        if isinstance(datainstance, W_DataInstance):
            ptr = datainstance.ll_buffer
        else:
            ptr = unwrap_truncate_int(rffi.VOIDP, space, w_arg)
        push_func(add_arg, argdesc, ptr)
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

def wrap_value(space, func, add_arg, argdesc, tp):
    letter, _, _ = tp
    for c, ll_type in ll_typemap_iter:
        if letter == c:
            if c in TYPEMAP_PTR_LETTERS:
                res = func(add_arg, argdesc, rffi.VOIDP)
                return space.wrap(rffi.cast(lltype.Unsigned, res))
            elif c == 'v':
                func(add_arg, argdesc, ll_type)
                return space.w_None
            elif c == 'q' or c == 'Q' or c == 'L' or c == 'c' or c == 'u':
                return space.wrap(func(add_arg, argdesc, ll_type))
            elif c == 'f' or c == 'd':
                return space.wrap(float(func(add_arg, argdesc, ll_type)))
            else:
                return space.wrap(intmask(func(add_arg, argdesc, ll_type)))
    raise OperationError(space.w_TypeError,
                         space.wrap("cannot directly read value"))
wrap_value._annspecialcase_ = 'specialize:arg(1)'

class W_FuncPtr(Wrappable):
    def __init__(self, space, ptr, argletters, resshape):
        self.ptr = ptr
        self.argletters = argletters
        self.resshape = resshape

    def getbuffer(space, self):
        return space.wrap(rffi.cast(lltype.Unsigned, self.ptr.funcsym))

    # XXX exactly the same as previous one, but arguments are suitable
    #     for calling with python
    def _getbuffer(self, space):
        return space.wrap(rffi.cast(lltype.Unsigned, self.ptr.funcsym))

    def byptr(self, space):
        from pypy.module._rawffi.array import get_array_cache
        array_of_ptr = get_array_cache(space).array_of_ptr
        array = array_of_ptr.allocate(space, 1)
        array.setitem(space, 0, self._getbuffer(space))
        if tracker.DO_TRACING:
            # XXX this is needed, because functions tend to live forever
            #     hence our testing is not performing that well
            del tracker.alloced[rffi.cast(lltype.Signed, array.ll_buffer)]
        return space.wrap(array)
    byptr.unwrap_spec = ['self', ObjSpace]

    def call(self, space, args_w):
        from pypy.module._rawffi.array import W_ArrayInstance
        from pypy.module._rawffi.structure import W_StructureInstance
        argnum = len(args_w)
        if argnum != len(self.argletters):
            msg = "Wrong number of argument: expected %d, got %d" % (
                len(self.argletters), argnum)
            raise OperationError(space.w_TypeError, space.wrap(msg))
        args_ll = []
        for i in range(argnum):
            argletter = self.argletters[i]
            w_arg = args_w[i]
            if argletter == 'V': # by value object
                arg = space.interp_w(W_StructureInstance, w_arg)
                xsize, xalignment = size_alignment(self.ptr.argtypes[i])
                if (arg.shape.size != xsize or
                    arg.shape.alignment != xalignment):
                    msg = ("Argument %d should be a structure of size %d and "
                           "alignment %d, "
                           "got instead size %d and alignment %d" %
                           (i+1, xsize, xalignment,
                            arg.shape.size, arg.shape.alignment))
                    raise OperationError(space.w_TypeError, space.wrap(msg))
            else:
                arg = space.interp_w(W_ArrayInstance, w_arg)
                if arg.length != 1:
                    msg = ("Argument %d should be an array of length 1, "
                           "got length %d" % (i+1, arg.length))
                    raise OperationError(space.w_TypeError, space.wrap(msg))
                letter = arg.shape.itemtp[0]
                if letter != argletter:
                    if not (argletter in TYPEMAP_PTR_LETTERS and
                            letter in TYPEMAP_PTR_LETTERS):
                        msg = "Argument %d should be typecode %s, got %s" % (
                            i+1, argletter, letter)
                        raise OperationError(space.w_TypeError, space.wrap(msg))
            args_ll.append(arg.ll_buffer)
            # XXX we could avoid the intermediate list args_ll
        if self.resshape is not None:
            result = self.resshape.allocate(space, 1, autofree=True)
            self.ptr.call(args_ll, result.ll_buffer)
            return space.wrap(result)
        else:
            self.ptr.call(args_ll, lltype.nullptr(rffi.VOIDP.TO))
            return space.w_None
    call.unwrap_spec = ['self', ObjSpace, 'args_w']

def descr_new_funcptr(space, w_tp, addr, w_args, w_res):
    ffi_args, args = unpack_argshapes(space, w_args)
    ffi_res, res = unpack_resshape(space, w_res)
    ptr = RawFuncPtr('???', ffi_args, ffi_res, rffi.cast(rffi.VOIDP, addr))
    return space.wrap(W_FuncPtr(space, ptr, args, res))
descr_new_funcptr.unwrap_spec = [ObjSpace, W_Root, r_uint, W_Root, W_Root]

W_FuncPtr.typedef = TypeDef(
    'FuncPtr',
    __new__  = interp2app(descr_new_funcptr),
    __call__ = interp2app(W_FuncPtr.call),
    buffer   = GetSetProperty(W_FuncPtr.getbuffer),
    byptr    = interp2app(W_FuncPtr.byptr),
)
W_FuncPtr.typedef.acceptable_as_base_class = False

def _create_new_accessor(func_name, name):
    def accessor(space, tp_letter):
        if len(tp_letter) != 1:
            raise OperationError(space.w_ValueError, space.wrap(
                "Expecting string of length one"))
        tp_letter = tp_letter[0] # fool annotator
        try:
            return space.wrap(intmask(getattr(TYPEMAP[tp_letter], name)))
        except KeyError:
            raise OperationError(space.w_ValueError, space.wrap(
                "Unknown type specification %s" % tp_letter))
    accessor.unwrap_spec = [ObjSpace, str]
    return func_with_new_name(accessor, func_name)

sizeof = _create_new_accessor('sizeof', 'c_size')
alignment = _create_new_accessor('alignment', 'c_alignment')

def charp2string(space, address, maxlength=sys.maxint):
    if address == 0:
        return space.w_None
    s = rffi.charp2strn(rffi.cast(rffi.CCHARP, address), maxlength)
    return space.wrap(s)
charp2string.unwrap_spec = [ObjSpace, r_uint, int]

def charp2rawstring(space, address, maxlength=-1):
    if maxlength == -1:
        return charp2string(space, address)
    s = rffi.charpsize2str(rffi.cast(rffi.CCHARP, address), maxlength)
    return space.wrap(s)
charp2rawstring.unwrap_spec = [ObjSpace, r_uint, int]

if _MS_WINDOWS:
    def FormatError(space, code):
        return space.wrap(rwin32.FormatError(code))
    FormatError.unwrap_spec = [ObjSpace, int]

    def check_HRESULT(space, hresult):
        if rwin32.FAILED(hresult):
            raise OperationError(space.w_WindowsError, space.wrap(hresult))
        return space.wrap(hresult)
    check_HRESULT.unwrap_spec = [ObjSpace, int]

def get_libc(space):
    try:
        return space.wrap(W_CDLL(space, libc_name))
    except OSError, e:
        raise wrap_oserror(space, e)
