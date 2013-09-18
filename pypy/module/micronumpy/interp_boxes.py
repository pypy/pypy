from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import operationerrfmt, OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.objspace.std.floattype import float_typedef
from pypy.objspace.std.stringtype import str_typedef
from pypy.objspace.std.unicodetype import unicode_typedef, unicode_from_object
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.complextype import complex_typedef
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rtyper.lltypesystem import rffi
from rpython.tool.sourcetools import func_with_new_name
from pypy.module.micronumpy.arrayimpl.voidbox import VoidBoxStorage
from rpython.rlib.objectmodel import specialize
from pypy.interpreter.mixedmodule import MixedModule
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.rstring import StringBuilder


MIXIN_32 = (W_IntObject.typedef,) if LONG_BIT == 32 else ()
MIXIN_64 = (W_IntObject.typedef,) if LONG_BIT == 64 else ()

# Is this the proper place for this?
ENABLED_LONG_DOUBLE = False
long_double_size = rffi.sizeof_c_type('long double', ignore_errors=True)

import os
if long_double_size == 8 and os.name == 'nt':
    # this is a lie, or maybe a wish, MS fakes longdouble math with double
    long_double_size = 12


def new_dtype_getter(name):
    def _get_dtype(space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        return get_dtype_cache(space).dtypes_by_name[name]

    def new(space, w_subtype, w_value):
        dtype = _get_dtype(space)
        return dtype.itemtype.coerce_subtype(space, w_subtype, w_value)

    def descr_reduce(self, space):
        return self.reduce(space)

    return func_with_new_name(new, name + "_box_new"), staticmethod(_get_dtype), func_with_new_name(descr_reduce, "descr_reduce")


class Box(object):
    _mixin_ = True

    def reduce(self, space):
        from rpython.rlib.rstring import StringBuilder
        from rpython.rtyper.lltypesystem import rffi, lltype

        numpypy = space.getbuiltinmodule("_numpypy")
        assert isinstance(numpypy, MixedModule)
        multiarray = numpypy.get("multiarray")
        assert isinstance(multiarray, MixedModule)
        scalar = multiarray.get("scalar")

        ret = space.newtuple([scalar, space.newtuple([space.wrap(self._get_dtype(space)), space.wrap(self.raw_str())])])
        return ret

class PrimitiveBox(Box):
    _mixin_ = True

    def __init__(self, value):
        self.value = value

    def convert_to(self, dtype):
        return dtype.box(self.value)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, self.value)

    def raw_str(self):
        value = lltype.malloc(rffi.CArray(lltype.typeOf(self.value)), 1, flavor="raw")
        value[0] = self.value

        builder = StringBuilder()
        builder.append_charpsize(rffi.cast(rffi.CCHARP, value), rffi.sizeof(lltype.typeOf(self.value)))
        ret = builder.build()

        lltype.free(value, flavor="raw")

        return ret

class ComplexBox(Box):
    _mixin_ = True

    def __init__(self, real, imag=0.):
        self.real = real
        self.imag = imag

    def convert_to(self, dtype):
        return dtype.box_complex(self.real, self.imag)

    def convert_real_to(self, dtype):
        return dtype.box(self.real)

    def convert_imag_to(self, dtype):
        return dtype.box(self.imag)

    def raw_str(self):
        value = lltype.malloc(rffi.CArray(lltype.typeOf(self.real)), 2, flavor="raw")
        value[0] = self.real
        value[1] = self.imag

        builder = StringBuilder()
        builder.append_charpsize(rffi.cast(rffi.CCHARP, value), rffi.sizeof(lltype.typeOf(self.real)) * 2)
        ret = builder.build()

        lltype.free(value, flavor="raw")

        return ret

class W_GenericBox(W_Root):
    _attrs_ = ()

    def descr__new__(space, w_subtype, __args__):
        raise operationerrfmt(space.w_TypeError,
                              "cannot create '%N' instances",
                              w_subtype)

    def get_dtype(self, space):
        return self._get_dtype(space)

    def descr_str(self, space):
        return space.wrap(self.get_dtype(space).itemtype.str_format(self))

    def descr_format(self, space, w_spec):
        return space.format(self.item(space), w_spec)

    def descr_int(self, space):
        box = self.convert_to(W_LongBox._get_dtype(space))
        assert isinstance(box, W_LongBox)
        return space.wrap(box.value)

    def descr_float(self, space):
        box = self.convert_to(W_Float64Box._get_dtype(space))
        assert isinstance(box, W_Float64Box)
        return space.wrap(box.value)

    def descr_nonzero(self, space):
        dtype = self.get_dtype(space)
        return space.wrap(dtype.itemtype.bool(self))

    def _binop_impl(ufunc_name):
        def impl(self, space, w_other, w_out=None):
            from pypy.module.micronumpy import interp_ufuncs
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space,
                                                            [self, w_other, w_out])
        return func_with_new_name(impl, "binop_%s_impl" % ufunc_name)

    def _binop_right_impl(ufunc_name):
        def impl(self, space, w_other, w_out=None):
            from pypy.module.micronumpy import interp_ufuncs
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space,
                                                            [w_other, self, w_out])
        return func_with_new_name(impl, "binop_right_%s_impl" % ufunc_name)

    def _unaryop_impl(ufunc_name):
        def impl(self, space, w_out=None):
            from pypy.module.micronumpy import interp_ufuncs
            return getattr(interp_ufuncs.get(space), ufunc_name).call(space,
                                                                    [self, w_out])
        return func_with_new_name(impl, "unaryop_%s_impl" % ufunc_name)

    descr_add = _binop_impl("add")
    descr_sub = _binop_impl("subtract")
    descr_mul = _binop_impl("multiply")
    descr_div = _binop_impl("divide")
    descr_truediv = _binop_impl("true_divide")
    descr_floordiv = _binop_impl("floor_divide")
    descr_mod = _binop_impl("mod")
    descr_pow = _binop_impl("power")
    descr_lshift = _binop_impl("left_shift")
    descr_rshift = _binop_impl("right_shift")
    descr_and = _binop_impl("bitwise_and")
    descr_or = _binop_impl("bitwise_or")
    descr_xor = _binop_impl("bitwise_xor")

    descr_eq = _binop_impl("equal")
    descr_ne = _binop_impl("not_equal")
    descr_lt = _binop_impl("less")
    descr_le = _binop_impl("less_equal")
    descr_gt = _binop_impl("greater")
    descr_ge = _binop_impl("greater_equal")

    descr_radd = _binop_right_impl("add")
    descr_rsub = _binop_right_impl("subtract")
    descr_rmul = _binop_right_impl("multiply")
    descr_rdiv = _binop_right_impl("divide")
    descr_rtruediv = _binop_right_impl("true_divide")
    descr_rfloordiv = _binop_right_impl("floor_divide")
    descr_rmod = _binop_right_impl("mod")
    descr_rpow = _binop_right_impl("power")
    descr_rlshift = _binop_right_impl("left_shift")
    descr_rrshift = _binop_right_impl("right_shift")
    descr_rand = _binop_right_impl("bitwise_and")
    descr_ror = _binop_right_impl("bitwise_or")
    descr_rxor = _binop_right_impl("bitwise_xor")

    descr_pos = _unaryop_impl("positive")
    descr_neg = _unaryop_impl("negative")
    descr_abs = _unaryop_impl("absolute")
    descr_invert = _unaryop_impl("invert")
    descr_conjugate = _unaryop_impl("conjugate")

    def descr_divmod(self, space, w_other):
        w_quotient = self.descr_div(space, w_other)
        w_remainder = self.descr_mod(space, w_other)
        return space.newtuple([w_quotient, w_remainder])

    def descr_rdivmod(self, space, w_other):
        w_quotient = self.descr_rdiv(space, w_other)
        w_remainder = self.descr_rmod(space, w_other)
        return space.newtuple([w_quotient, w_remainder])

    def descr_hash(self, space):
        return space.hash(self.item(space))

    def item(self, space):
        return self.get_dtype(space).itemtype.to_builtin_type(space, self)

    def descr_any(self, space):
        value = space.is_true(self)
        return space.wrap(W_BoolBox(value))

    def descr_all(self, space):
        value = space.is_true(self)
        return space.wrap(W_BoolBox(value))

    def descr_ravel(self, space):
        from pypy.module.micronumpy.base import convert_to_array
        w_values = space.newtuple([self])
        return convert_to_array(space, w_values)

    @unwrap_spec(decimals=int)
    def descr_round(self, space, decimals=0):
        v = self.convert_to(self.get_dtype(space))
        return self.get_dtype(space).itemtype.round(v, decimals)

    def descr_view(self, space, w_dtype):
        from pypy.module.micronumpy.interp_dtype import W_Dtype
        dtype = space.interp_w(W_Dtype,
            space.call_function(space.gettypefor(W_Dtype), w_dtype))
        if dtype.get_size() != self.get_dtype(space).get_size():
            raise OperationError(space.w_ValueError, space.wrap(
                "new type not compatible with array."))
        raise OperationError(space.w_NotImplementedError, space.wrap(
            "view not implelemnted yet"))

class W_BoolBox(W_GenericBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("bool")

class W_NumberBox(W_GenericBox):
    _attrs_ = ()

class W_IntegerBox(W_NumberBox):
    def int_w(self, space):
        return space.int_w(self.descr_int(space))

class W_SignedIntegerBox(W_IntegerBox):
    pass

class W_UnsignedIntegerBox(W_IntegerBox):
    pass

class W_Int8Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("int8")

class W_UInt8Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("uint8")

class W_Int16Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("int16")

class W_UInt16Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("uint16")

class W_Int32Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("int32")

class W_UInt32Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("uint32")

class W_LongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("long")

class W_ULongBox(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("ulong")

class W_Int64Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("int64")

class W_LongLongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter('longlong')

class W_UInt64Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("uint64")

class W_ULongLongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter('ulonglong')

class W_InexactBox(W_NumberBox):
    _attrs_ = ()

class W_FloatingBox(W_InexactBox):
    _attrs_ = ()

class W_Float16Box(W_FloatingBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("float16")

class W_Float32Box(W_FloatingBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("float32")

class W_Float64Box(W_FloatingBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("float64")

class W_FlexibleBox(W_GenericBox):
    _attrs_ = ['ofs', 'dtype', 'arr']
    _immutable_fields_ = ['ofs']
    def __init__(self, arr, ofs, dtype):
        self.arr = arr # we have to keep array alive
        self.ofs = ofs
        self.dtype = dtype

    def get_dtype(self, space):
        return self.arr.dtype

@unwrap_spec(self=W_GenericBox)
def descr_index(space, self):
    return space.index(self.item(space))


class W_VoidBox(W_FlexibleBox):
    def descr_getitem(self, space, w_item):
        from pypy.module.micronumpy.types import VoidType
        if space.isinstance_w(w_item, space.w_str):
            item = space.str_w(w_item)
        elif space.isinstance_w(w_item, space.w_int):
            #Called by iterator protocol
            indx = space.int_w(w_item)
            try:
                item = self.dtype.fieldnames[indx]
            except IndexError:
                raise OperationError(space.w_IndexError,
                     space.wrap("Iterated over too many fields %d" % indx))
        else:
            raise OperationError(space.w_IndexError, space.wrap(
                    "Can only access fields of record with int or str"))
        try:
            ofs, dtype = self.dtype.fields[item]
        except KeyError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("Field %s does not exist" % item))
        if isinstance(dtype.itemtype, VoidType):
            read_val = dtype.itemtype.readarray(self.arr, self.ofs, ofs, dtype)
        else:
            read_val = dtype.itemtype.read(self.arr, self.ofs, ofs, dtype)
        if isinstance (read_val, W_StringBox):
            # StringType returns a str
            return space.wrap(dtype.itemtype.to_str(read_val))
        return read_val

    @unwrap_spec(item=str)
    def descr_setitem(self, space, item, w_value):
        try:
            ofs, dtype = self.dtype.fields[item]
        except KeyError:
            raise OperationError(space.w_IndexError,
                                 space.wrap("Field %s does not exist" % item))
        dtype.itemtype.store(self.arr, self.ofs, ofs,
                             dtype.coerce(space, w_value))

    def convert_to(self, dtype):
        # if we reach here, the record fields are guarenteed to match.
        return self

class W_CharacterBox(W_FlexibleBox):
    def convert_to(self, dtype):
        # XXX assert dtype is str type
        return self


class W_StringBox(W_CharacterBox):
    def descr__new__string_box(space, w_subtype, w_arg):
        from pypy.module.micronumpy.interp_dtype import new_string_dtype
        arg = space.str_w(space.str(w_arg))
        arr = VoidBoxStorage(len(arg), new_string_dtype(space, len(arg)))
        for i in range(len(arg)):
            arr.storage[i] = arg[i]
        return W_StringBox(arr, 0, arr.dtype)


class W_UnicodeBox(W_CharacterBox):
    def descr__new__unicode_box(space, w_subtype, w_arg):
        raise OperationError(space.w_NotImplementedError, space.wrap("Unicode is not supported yet"))

        from pypy.module.micronumpy.interp_dtype import new_unicode_dtype

        arg = space.unicode_w(unicode_from_object(space, w_arg))
        # XXX size computations, we need tests anyway
        arr = VoidBoxStorage(len(arg), new_unicode_dtype(space, len(arg)))
        # XXX not this way, we need store
        #for i in range(len(arg)):
        #    arr.storage[i] = arg[i]
        return W_UnicodeBox(arr, 0, arr.dtype)


class W_ComplexFloatingBox(W_InexactBox):
    _attrs_ = ()
    def descr_get_real(self, space):
        dtype = self._COMPONENTS_BOX._get_dtype(space)
        box = self.convert_real_to(dtype)
        assert isinstance(box, self._COMPONENTS_BOX)
        return space.wrap(box)

    def descr_get_imag(self, space):
        dtype = self._COMPONENTS_BOX._get_dtype(space)
        box = self.convert_imag_to(dtype)
        assert isinstance(box, self._COMPONENTS_BOX)
        return space.wrap(box)


class W_Complex64Box(ComplexBox, W_ComplexFloatingBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("complex64")
    _COMPONENTS_BOX = W_Float32Box


class W_Complex128Box(ComplexBox, W_ComplexFloatingBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter("complex128")
    _COMPONENTS_BOX = W_Float64Box

if ENABLED_LONG_DOUBLE and long_double_size == 12:
    class W_Float96Box(W_FloatingBox, PrimitiveBox):
        descr__new__, _get_dtype, descr_reduce = new_dtype_getter("float96")

    W_LongDoubleBox = W_Float96Box

    class W_Complex192Box(ComplexBox, W_ComplexFloatingBox):
        descr__new__, _get_dtype, descr_reduce = new_dtype_getter("complex192")
        _COMPONENTS_BOX = W_Float96Box

    W_CLongDoubleBox = W_Complex192Box

elif ENABLED_LONG_DOUBLE and long_double_size == 16:
    class W_Float128Box(W_FloatingBox, PrimitiveBox):
        descr__new__, _get_dtype, descr_reduce = new_dtype_getter("float128")
    W_LongDoubleBox = W_Float128Box

    class W_Complex256Box(ComplexBox, W_ComplexFloatingBox):
        descr__new__, _get_dtype, descr_reduce = new_dtype_getter("complex256")
        _COMPONENTS_BOX = W_Float128Box

    W_CLongDoubleBox = W_Complex256Box

elif ENABLED_LONG_DOUBLE:
    W_LongDoubleBox = W_Float64Box
    W_CLongDoubleBox = W_Complex64Box


W_GenericBox.typedef = TypeDef("generic",
    __module__ = "numpypy",

    __new__ = interp2app(W_GenericBox.descr__new__.im_func),

    __str__ = interp2app(W_GenericBox.descr_str),
    __repr__ = interp2app(W_GenericBox.descr_str),
    __format__ = interp2app(W_GenericBox.descr_format),
    __int__ = interp2app(W_GenericBox.descr_int),
    __float__ = interp2app(W_GenericBox.descr_float),
    __nonzero__ = interp2app(W_GenericBox.descr_nonzero),

    __add__ = interp2app(W_GenericBox.descr_add),
    __sub__ = interp2app(W_GenericBox.descr_sub),
    __mul__ = interp2app(W_GenericBox.descr_mul),
    __div__ = interp2app(W_GenericBox.descr_div),
    __truediv__ = interp2app(W_GenericBox.descr_truediv),
    __floordiv__ = interp2app(W_GenericBox.descr_floordiv),
    __mod__ = interp2app(W_GenericBox.descr_mod),
    __divmod__ = interp2app(W_GenericBox.descr_divmod),
    __pow__ = interp2app(W_GenericBox.descr_pow),
    __lshift__ = interp2app(W_GenericBox.descr_lshift),
    __rshift__ = interp2app(W_GenericBox.descr_rshift),
    __and__ = interp2app(W_GenericBox.descr_and),
    __or__ = interp2app(W_GenericBox.descr_or),
    __xor__ = interp2app(W_GenericBox.descr_xor),

    __radd__ = interp2app(W_GenericBox.descr_radd),
    __rsub__ = interp2app(W_GenericBox.descr_rsub),
    __rmul__ = interp2app(W_GenericBox.descr_rmul),
    __rdiv__ = interp2app(W_GenericBox.descr_rdiv),
    __rtruediv__ = interp2app(W_GenericBox.descr_rtruediv),
    __rfloordiv__ = interp2app(W_GenericBox.descr_rfloordiv),
    __rmod__ = interp2app(W_GenericBox.descr_rmod),
    __rdivmod__ = interp2app(W_GenericBox.descr_rdivmod),
    __rpow__ = interp2app(W_GenericBox.descr_rpow),
    __rlshift__ = interp2app(W_GenericBox.descr_rlshift),
    __rrshift__ = interp2app(W_GenericBox.descr_rrshift),
    __rand__ = interp2app(W_GenericBox.descr_rand),
    __ror__ = interp2app(W_GenericBox.descr_ror),
    __rxor__ = interp2app(W_GenericBox.descr_rxor),

    __eq__ = interp2app(W_GenericBox.descr_eq),
    __ne__ = interp2app(W_GenericBox.descr_ne),
    __lt__ = interp2app(W_GenericBox.descr_lt),
    __le__ = interp2app(W_GenericBox.descr_le),
    __gt__ = interp2app(W_GenericBox.descr_gt),
    __ge__ = interp2app(W_GenericBox.descr_ge),

    __pos__ = interp2app(W_GenericBox.descr_pos),
    __neg__ = interp2app(W_GenericBox.descr_neg),
    __abs__ = interp2app(W_GenericBox.descr_abs),
    __invert__ = interp2app(W_GenericBox.descr_invert),

    __hash__ = interp2app(W_GenericBox.descr_hash),

    tolist = interp2app(W_GenericBox.item),
    any = interp2app(W_GenericBox.descr_any),
    all = interp2app(W_GenericBox.descr_all),
    ravel = interp2app(W_GenericBox.descr_ravel),
    round = interp2app(W_GenericBox.descr_round),
    conjugate = interp2app(W_GenericBox.descr_conjugate),
    view = interp2app(W_GenericBox.descr_view),
)

W_BoolBox.typedef = TypeDef("bool_", W_GenericBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_BoolBox.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_BoolBox.descr_reduce),
)

W_NumberBox.typedef = TypeDef("number", W_GenericBox.typedef,
    __module__ = "numpypy",
)

W_IntegerBox.typedef = TypeDef("integer", W_NumberBox.typedef,
    __module__ = "numpypy",
)

W_SignedIntegerBox.typedef = TypeDef("signedinteger", W_IntegerBox.typedef,
    __module__ = "numpypy",
)

W_UnsignedIntegerBox.typedef = TypeDef("unsignedinteger", W_IntegerBox.typedef,
    __module__ = "numpypy",
)

W_Int8Box.typedef = TypeDef("int8", W_SignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int8Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_Int8Box.descr_reduce),
)

W_UInt8Box.typedef = TypeDef("uint8", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt8Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_UInt8Box.descr_reduce),
)

W_Int16Box.typedef = TypeDef("int16", W_SignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int16Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_Int16Box.descr_reduce),
)

W_UInt16Box.typedef = TypeDef("uint16", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt16Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_UInt16Box.descr_reduce),
)

W_Int32Box.typedef = TypeDef("int32", (W_SignedIntegerBox.typedef,) + MIXIN_32,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int32Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_Int32Box.descr_reduce),
)

W_UInt32Box.typedef = TypeDef("uint32", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt32Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_UInt32Box.descr_reduce),
)

W_Int64Box.typedef = TypeDef("int64", (W_SignedIntegerBox.typedef,) + MIXIN_64,
    __module__ = "numpypy",
    __new__ = interp2app(W_Int64Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_Int64Box.descr_reduce),
)

if LONG_BIT == 32:
    W_LongBox = W_Int32Box
    W_ULongBox = W_UInt32Box
elif LONG_BIT == 64:
    W_LongBox = W_Int64Box
    W_ULongBox = W_UInt64Box

W_UInt64Box.typedef = TypeDef("uint64", W_UnsignedIntegerBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_UInt64Box.descr__new__.im_func),
    __index__ = interp2app(descr_index),
    __reduce__ = interp2app(W_UInt64Box.descr_reduce),
)

W_InexactBox.typedef = TypeDef("inexact", W_NumberBox.typedef,
    __module__ = "numpypy",
)

W_FloatingBox.typedef = TypeDef("floating", W_InexactBox.typedef,
    __module__ = "numpypy",
)

W_Float16Box.typedef = TypeDef("float16", W_FloatingBox.typedef,
    __module__ = "numpypy",

    __new__ = interp2app(W_Float16Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Float16Box.descr_reduce),
)

W_Float32Box.typedef = TypeDef("float32", W_FloatingBox.typedef,
    __module__ = "numpypy",

    __new__ = interp2app(W_Float32Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Float32Box.descr_reduce),
)

W_Float64Box.typedef = TypeDef("float64", (W_FloatingBox.typedef, float_typedef),
    __module__ = "numpypy",

    __new__ = interp2app(W_Float64Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Float64Box.descr_reduce),
)

if ENABLED_LONG_DOUBLE and long_double_size == 12:
    W_Float96Box.typedef = TypeDef("float96", (W_FloatingBox.typedef),
        __module__ = "numpypy",
        __reduce__ = interp2app(W_Float96Box.descr_reduce),

        __new__ = interp2app(W_Float96Box.descr__new__.im_func),
    )

    W_Complex192Box.typedef = TypeDef("complex192", (W_ComplexFloatingBox.typedef, complex_typedef),
        __module__ = "numpypy",
        __new__ = interp2app(W_Complex192Box.descr__new__.im_func),
        __reduce__ = interp2app(W_Complex192Box.descr_reduce),
        real = GetSetProperty(W_ComplexFloatingBox.descr_get_real),
        imag = GetSetProperty(W_ComplexFloatingBox.descr_get_imag),
    )

elif ENABLED_LONG_DOUBLE and long_double_size == 16:
    W_Float128Box.typedef = TypeDef("float128", (W_FloatingBox.typedef),
        __module__ = "numpypy",

        __new__ = interp2app(W_Float128Box.descr__new__.im_func),
        __reduce__ = interp2app(W_Float128Box.descr_reduce),
    )

    W_Complex256Box.typedef = TypeDef("complex256", (W_ComplexFloatingBox.typedef, complex_typedef),
        __module__ = "numpypy",
        __new__ = interp2app(W_Complex256Box.descr__new__.im_func),
        __reduce__ = interp2app(W_Complex256Box.descr_reduce),
        real = GetSetProperty(W_ComplexFloatingBox.descr_get_real),
        imag = GetSetProperty(W_ComplexFloatingBox.descr_get_imag),
    )

W_FlexibleBox.typedef = TypeDef("flexible", W_GenericBox.typedef,
    __module__ = "numpypy",
)

W_VoidBox.typedef = TypeDef("void", W_FlexibleBox.typedef,
    __module__ = "numpypy",
    __new__ = interp2app(W_VoidBox.descr__new__.im_func),
    __getitem__ = interp2app(W_VoidBox.descr_getitem),
    __setitem__ = interp2app(W_VoidBox.descr_setitem),
)

W_CharacterBox.typedef = TypeDef("character", W_FlexibleBox.typedef,
    __module__ = "numpypy",
)

W_StringBox.typedef = TypeDef("string_", (W_CharacterBox.typedef, str_typedef),
    __module__ = "numpypy",
    __new__ = interp2app(W_StringBox.descr__new__string_box.im_func),
)

W_UnicodeBox.typedef = TypeDef("unicode_", (W_CharacterBox.typedef, unicode_typedef),
    __module__ = "numpypy",
    __new__ = interp2app(W_UnicodeBox.descr__new__unicode_box.im_func),
)

W_ComplexFloatingBox.typedef = TypeDef("complexfloating", W_InexactBox.typedef,
    __module__ = "numpypy",
)


W_Complex128Box.typedef = TypeDef("complex128", (W_ComplexFloatingBox.typedef, complex_typedef),
    __module__ = "numpypy",
    __new__ = interp2app(W_Complex128Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Complex128Box.descr_reduce),
    real = GetSetProperty(W_ComplexFloatingBox.descr_get_real),
    imag = GetSetProperty(W_ComplexFloatingBox.descr_get_imag),
)

W_Complex64Box.typedef = TypeDef("complex64", (W_ComplexFloatingBox.typedef),
    __module__ = "numpypy",
    __new__ = interp2app(W_Complex64Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Complex64Box.descr_reduce),
    real = GetSetProperty(W_ComplexFloatingBox .descr_get_real),
    imag = GetSetProperty(W_ComplexFloatingBox.descr_get_imag),
)
