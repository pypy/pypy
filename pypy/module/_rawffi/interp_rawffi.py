import sys
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable, \
     Arguments
from pypy.interpreter.error import OperationError, wrap_oserror
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty

from pypy.rlib.libffi import *
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.unroll import unrolling_iterable

from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.rarithmetic import intmask, r_uint, r_singlefloat
from pypy.module._rawffi.tracker import tracker

def _signed_type_for(TYPE):
    sz = rffi.sizeof(TYPE)
    if sz == 4:   return ffi_type_sint32
    elif sz == 8: return ffi_type_sint64
    else: raise ValueError("unsupported type size for %r" % (TYPE,))

def _unsigned_type_for(TYPE):
    sz = rffi.sizeof(TYPE)
    if sz == 4:   return ffi_type_uint32
    elif sz == 8: return ffi_type_uint64
    else: raise ValueError("unsupported type size for %r" % (TYPE,))

TYPEMAP = {
    # XXX A mess with unsigned/signed/normal chars :-/
    'c' : ffi_type_uchar,
    'b' : ffi_type_schar,
    'B' : ffi_type_uchar,
    'h' : ffi_type_sshort,
    'u' : ffi_type_uint, # XXX think deeper how to map it properly
    'H' : ffi_type_ushort,
    'i' : ffi_type_sint,
    'I' : ffi_type_uint,
    # xxx don't use ffi_type_slong and ffi_type_ulong - their meaning
    # changes from a libffi version to another :-((
    'l' : _signed_type_for(rffi.LONG),
    'L' : _unsigned_type_for(rffi.ULONG),
    'q' : _signed_type_for(rffi.LONGLONG),
    'Q' : _unsigned_type_for(rffi.ULONGLONG),
    'f' : ffi_type_float,
    'd' : ffi_type_double,
    's' : ffi_type_pointer,
    'P' : ffi_type_pointer,
    'z' : ffi_type_pointer,
    'O' : ffi_type_pointer,
    'Z' : ffi_type_pointer,
}
TYPEMAP_PTR_LETTERS = "POszZ"

UNPACKED_TYPECODES = dict([(code, (code,
                                   intmask(field_desc.c_size),
                                   intmask(field_desc.c_alignment)))
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

def unpack_typecode(space, w_typecode):
    if space.is_true(space.isinstance(w_typecode, space.w_str)):
        letter = space.str_w(w_typecode)
        return letter2tp(space, letter)
    else:
        w_size, w_align = space.unpacktuple(w_typecode, expected_length=2)
        return ('V', space.int_w(w_size), space.int_w(w_align)) # value object

def _get_type_(space, key):
    try:
        return TYPEMAP[key]
    except KeyError:
        raise OperationError(space.w_ValueError, space.wrap(
            "Unknown type letter %s" % (key,)))

class W_CDLL(Wrappable):
    def __init__(self, space, name):
        self.cdll = CDLL(name)
        self.name = name
        self.w_cache = space.newdict()
        self.space = space

    def get_arg_type(self, letter, argsize, argalignment):
        space = self.space
        if letter == 'V': # xxx leaks
            return make_struct_ffitype(argsize, argalignment)
        else:
            return _get_type_(space, letter)

    def get_type(self, key):
        space = self.space
        return _get_type_(space, key)

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
        argtypes = [unpack_typecode(space, w_arg) for w_arg in argtypes_w]
        ffi_argtypes = [self.get_arg_type(letter, argsize, argalignment)
                                               for letter, argsize, argalignment
                                                    in argtypes]
        try:
            ptr = self.cdll.getrawpointer(name, ffi_argtypes, ffi_restype)
            w_funcptr = W_FuncPtr(space, ptr, argtypes, restype)
            space.setitem(self.w_cache, w_key, w_funcptr)
            return w_funcptr
        except KeyError:
            raise OperationError(space.w_AttributeError, space.wrap(
                "No symbol %s found in library %s" % (name, self.name)))
    ptr.unwrap_spec = ['self', ObjSpace, str, W_Root, W_Root]

    def getprimitive(self, space, letter, name):
        from pypy.module._rawffi.array import get_array_cache
        cache = get_array_cache(space)
        w_array = cache.get_array_type(letter2tp(space, letter))
        try:
            address_as_uint = rffi.cast(lltype.Unsigned,
                                        self.cdll.getaddressindll(name))
        except KeyError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("Cannot find symbol %s" % (name,)))
        return w_array.fromaddress(space, address_as_uint, 1)
    getprimitive.unwrap_spec = ['self', ObjSpace, str, str]

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
    getprimitive= interp2app(W_CDLL.getprimitive),
    __doc__     = """ C Dynamically loaded library
use CDLL(libname) to create a handle to a C library (the argument is processed
the same way as dlopen processes it). On such a library you can call:
lib.ptr(func_name, argtype_list, restype)

where argtype_list is a list of single characters and restype is a single
character. The character meanings are more or less the same as in the struct
module, except that s has trailing \x00 added, while p is considered a raw
buffer."""
)

unroll_letters_for_numbers = unrolling_iterable("bBhHiIlLqQ")

def segfault_exception(space, reason):
    w_mod = space.getbuiltinmodule("_rawffi")
    w_exception = space.getattr(w_mod, space.wrap("SegfaultException"))
    return OperationError(w_exception, space.wrap(reason))


class W_DataInstance(Wrappable):
    def __init__(self, space, size, address=r_uint(0)):
        if address:
            self.ll_buffer = rffi.cast(rffi.VOIDP, address)
        else:
            self.ll_buffer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw',
                                           zero=True)
            if tracker.DO_TRACING:
                ll_buf = rffi.cast(rffi.INT, self.ll_buffer)
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
            ll_buf = rffi.cast(rffi.INT, self.ll_buffer)
            tracker.trace_free(ll_buf)
        lltype.free(self.ll_buffer, flavor='raw')
        self.ll_buffer = lltype.nullptr(rffi.VOIDP.TO)

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
                "Expected unicode string og length one as wide character"))
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
    def __init__(self, space, ptr, argtypes, restype):
        from pypy.module._rawffi.array import get_array_cache
        self.ptr = ptr
        if restype != 'v':
            cache = get_array_cache(space)
            self.resarray = cache.get_array_type(letter2tp(space, restype))
        else:
            self.resarray = None
        self.argtypes = argtypes

    def call(self, space, args_w):
        from pypy.module._rawffi.array import W_ArrayInstance
        from pypy.module._rawffi.structure import W_StructureInstance
        argnum = len(args_w)
        if argnum != len(self.argtypes):
            msg = "Wrong number of argument: expected %d, got %d" % (
                len(self.argtypes), argnum)
            raise OperationError(space.w_TypeError, space.wrap(msg))
        args_ll = []
        for i in range(argnum):
            argtype_letter, argtype_size, argtype_alignment = self.argtypes[i]
            w_arg = args_w[i]
            if argtype_letter == 'V': # by value object
                arg = space.interp_w(W_StructureInstance, w_arg)
                if (arg.shape.size != argtype_size or
                    arg.shape.alignment != argtype_alignment):
                    msg = ("Argument %d should be a structure of size %d and "
                           "alignment %d, "
                           "got instead size %d and alignment %d" %
                           (i+1, argtype_size, argtype_alignment,
                            arg.shape.size, arg.shape.alignment))
                    raise OperationError(space.w_TypeError, space.wrap(msg))
            else:
                arg = space.interp_w(W_ArrayInstance, w_arg)
                if arg.length != 1:
                    msg = ("Argument %d should be an array of length 1, "
                           "got length %d" % (i+1, arg.length))
                    raise OperationError(space.w_TypeError, space.wrap(msg))
                letter = arg.shape.itemtp[0]
                if letter != argtype_letter:
                    if not (argtype_letter in TYPEMAP_PTR_LETTERS and
                            letter in TYPEMAP_PTR_LETTERS):
                        msg = "Argument %d should be typecode %s, got %s" % (
                            i+1, argtype_letter, letter)
                        raise OperationError(space.w_TypeError, space.wrap(msg))
            args_ll.append(arg.ll_buffer)
            # XXX we could avoid the intermediate list args_ll
        if self.resarray is not None:
            result = self.resarray.allocate(space, 1)
            self.ptr.call(args_ll, result.ll_buffer)
            return space.wrap(result)
        else:
            self.ptr.call(args_ll, lltype.nullptr(rffi.VOIDP.TO))
            return space.w_None
    call.unwrap_spec = ['self', ObjSpace, 'args_w']

W_FuncPtr.typedef = TypeDef(
    'FuncPtr',
    __call__ = interp2app(W_FuncPtr.call)
)

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
