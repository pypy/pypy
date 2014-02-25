from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.objspace.std.bytesobject import W_BytesObject
from pypy.objspace.std.floattype import float_typedef
from pypy.objspace.std.unicodeobject import W_UnicodeObject
from pypy.objspace.std.intobject import W_IntObject
from pypy.objspace.std.complextype import complex_typedef
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rtyper.lltypesystem import rffi
from rpython.tool.sourcetools import func_with_new_name
from pypy.module.micronumpy.arrayimpl.voidbox import VoidBoxStorage
from pypy.module.micronumpy.base import W_NDimArray
from pypy.module.micronumpy.interp_flagsobj import W_FlagsObject
from pypy.interpreter.mixedmodule import MixedModule
from rpython.rtyper.lltypesystem import lltype
from rpython.rlib.rstring import StringBuilder
from rpython.rlib.objectmodel import specialize
from pypy.module.micronumpy import constants as NPY


MIXIN_32 = (W_IntObject.typedef,) if LONG_BIT == 32 else ()
MIXIN_64 = (W_IntObject.typedef,) if LONG_BIT == 64 else ()

#long_double_size = rffi.sizeof_c_type('long double', ignore_errors=True)
#import os
#if long_double_size == 8 and os.name == 'nt':
#    # this is a lie, or maybe a wish, MS fakes longdouble math with double
#    long_double_size = 12

# hardcode to 8 for now (simulate using normal double) until long double works
long_double_size = 8


def new_dtype_getter(num):
    @specialize.memo()
    def _get_dtype(space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        return get_dtype_cache(space).dtypes_by_num[num]

    def descr__new__(space, w_subtype, w_value=None):
        from pypy.module.micronumpy.interp_numarray import array
        dtype = _get_dtype(space)
        if not space.is_none(w_value):
            w_arr = array(space, w_value, dtype, copy=False)
            if len(w_arr.get_shape()) != 0:
                return w_arr
            w_value = w_arr.get_scalar_value().item(space)
        return dtype.itemtype.coerce_subtype(space, w_subtype, w_value)

    def descr_reduce(self, space):
        return self.reduce(space)

    return (func_with_new_name(descr__new__, 'descr__new__%d' % num),
            staticmethod(_get_dtype),
            descr_reduce)


class Box(object):
    _mixin_ = True

    def reduce(self, space):
        numpypy = space.getbuiltinmodule("_numpypy")
        assert isinstance(numpypy, MixedModule)
        multiarray = numpypy.get("multiarray")
        assert isinstance(multiarray, MixedModule)
        scalar = multiarray.get("scalar")

        ret = space.newtuple([scalar, space.newtuple([space.wrap(self._get_dtype(space)), space.wrap(self.raw_str())])])
        return ret

class PrimitiveBox(Box):
    _mixin_ = True
    _immutable_fields_ = ['value']

    def __init__(self, value):
        self.value = value

    def convert_to(self, space, dtype):
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
    _immutable_fields_ = ['real', 'imag']

    def __init__(self, real, imag=0.):
        self.real = real
        self.imag = imag

    def convert_to(self, space, dtype):
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
    _attrs_ = ['w_flags']

    def descr__new__(space, w_subtype, __args__):
        raise oefmt(space.w_TypeError,
                    "cannot create '%N' instances", w_subtype)

    def get_dtype(self, space):
        return self._get_dtype(space)

    def item(self, space):
        return self.get_dtype(space).itemtype.to_builtin_type(space, self)

    def descr_getitem(self, space, w_item):
        from pypy.module.micronumpy.base import convert_to_array
        if space.is_w(w_item, space.w_Ellipsis) or \
                (space.isinstance_w(w_item, space.w_tuple) and
                    space.len_w(w_item) == 0):
            return convert_to_array(space, self)
        raise OperationError(space.w_IndexError, space.wrap(
            "invalid index to scalar variable"))

    def descr_str(self, space):
        return space.wrap(self.get_dtype(space).itemtype.str_format(self))

    def descr_format(self, space, w_spec):
        return space.format(self.item(space), w_spec)

    def descr_hash(self, space):
        return space.hash(self.item(space))

    def descr_index(self, space):
        return space.index(self.item(space))

    def descr_int(self, space):
        if isinstance(self, W_UnsignedIntegerBox):
            box = self.convert_to(space, W_UInt64Box._get_dtype(space))
        else:
            box = self.convert_to(space, W_Int64Box._get_dtype(space))
        return space.int(box.item(space))

    def descr_long(self, space):
        if isinstance(self, W_UnsignedIntegerBox):
            box = self.convert_to(space, W_UInt64Box._get_dtype(space))
        else:
            box = self.convert_to(space, W_Int64Box._get_dtype(space))
        return space.long(box.item(space))

    def descr_float(self, space):
        box = self.convert_to(space, W_Float64Box._get_dtype(space))
        return space.float(box.item(space))

    def descr_oct(self, space):
        return space.oct(self.descr_int(space))

    def descr_hex(self, space):
        return space.hex(self.descr_int(space))

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

    def descr_any(self, space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        value = space.is_true(self)
        return get_dtype_cache(space).w_booldtype.box(value)

    def descr_all(self, space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        value = space.is_true(self)
        return get_dtype_cache(space).w_booldtype.box(value)

    def descr_zero(self, space):
        from pypy.module.micronumpy.interp_dtype import get_dtype_cache
        return get_dtype_cache(space).w_longdtype.box(0)

    def descr_ravel(self, space):
        from pypy.module.micronumpy.base import convert_to_array
        w_values = space.newtuple([self])
        return convert_to_array(space, w_values)

    @unwrap_spec(decimals=int)
    def descr_round(self, space, decimals=0, w_out=None):
        if not space.is_none(w_out):
            raise OperationError(space.w_NotImplementedError, space.wrap(
                "out not supported"))
        return self.get_dtype(space).itemtype.round(self, decimals)

    def descr_astype(self, space, w_dtype):
        from pypy.module.micronumpy.interp_dtype import W_Dtype
        dtype = space.interp_w(W_Dtype,
            space.call_function(space.gettypefor(W_Dtype), w_dtype))
        return self.convert_to(space, dtype)

    def descr_view(self, space, w_dtype):
        from pypy.module.micronumpy.interp_dtype import W_Dtype
        try:
            subclass = space.is_true(space.issubtype(
                w_dtype, space.gettypefor(W_NDimArray)))
        except OperationError, e:
            if e.match(space, space.w_TypeError):
                subclass = False
            else:
                raise
        if subclass:
            dtype = self.get_dtype(space)
        else:
            dtype = space.interp_w(W_Dtype,
                space.call_function(space.gettypefor(W_Dtype), w_dtype))
            if dtype.elsize == 0:
                raise OperationError(space.w_TypeError, space.wrap(
                    "data-type must not be 0-sized"))
            if dtype.elsize != self.get_dtype(space).elsize:
                raise OperationError(space.w_ValueError, space.wrap(
                    "new type not compatible with array."))
        if dtype.is_str_or_unicode():
            return dtype.coerce(space, space.wrap(self.raw_str()))
        elif dtype.is_record():
            raise OperationError(space.w_NotImplementedError, space.wrap(
                "viewing scalar as record not implemented"))
        else:
            return dtype.itemtype.runpack_str(space, self.raw_str())

    def descr_self(self, space):
        return self

    def descr_get_dtype(self, space):
        return self.get_dtype(space)

    def descr_get_size(self, space):
        return space.wrap(1)

    def descr_get_itemsize(self, space):
        return space.wrap(self.get_dtype(space).elsize)

    def descr_get_shape(self, space):
        return space.newtuple([])

    def descr_get_ndim(self, space):
        return space.wrap(0)

    def descr_copy(self, space):
        return self.convert_to(space, self.get_dtype(space))

    def descr_buffer(self, space):
        return self.descr_ravel(space).descr_get_data(space)

    def descr_byteswap(self, space):
        return self.get_dtype(space).itemtype.byteswap(self)

    def descr_tostring(self, space, __args__):
        w_meth = space.getattr(self.descr_ravel(space), space.wrap('tostring'))
        return space.call_args(w_meth, __args__)

    def descr_reshape(self, space, __args__):
        w_meth = space.getattr(self.descr_ravel(space), space.wrap('reshape'))
        return space.call_args(w_meth, __args__)

    def descr_get_real(self, space):
        return self.get_dtype(space).itemtype.real(self)

    def descr_get_imag(self, space):
        return self.get_dtype(space).itemtype.imag(self)

    w_flags = None
    def descr_get_flags(self, space):
        if self.w_flags is None:
            self.w_flags = W_FlagsObject(self)
        return self.w_flags

class W_BoolBox(W_GenericBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.BOOL)

class W_NumberBox(W_GenericBox):
    pass

class W_IntegerBox(W_NumberBox):
    def int_w(self, space):
        return space.int_w(self.descr_int(space))

class W_SignedIntegerBox(W_IntegerBox):
    pass

class W_UnsignedIntegerBox(W_IntegerBox):
    pass

class W_Int8Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.BYTE)

class W_UInt8Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.UBYTE)

class W_Int16Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.SHORT)

class W_UInt16Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.USHORT)

class W_Int32Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.INT)

class W_UInt32Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.UINT)

class W_LongBox(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.LONG)

class W_ULongBox(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.ULONG)

class W_Int64Box(W_SignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.LONGLONG)

class W_UInt64Box(W_UnsignedIntegerBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.ULONGLONG)

class W_InexactBox(W_NumberBox):
    pass

class W_FloatingBox(W_InexactBox):
    pass

class W_Float16Box(W_FloatingBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.HALF)

class W_Float32Box(W_FloatingBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.FLOAT)

class W_Float64Box(W_FloatingBox, PrimitiveBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.DOUBLE)

    def descr_as_integer_ratio(self, space):
        return space.call_method(self.item(space), 'as_integer_ratio')

class W_ComplexFloatingBox(W_InexactBox):
    pass

class W_Complex64Box(ComplexBox, W_ComplexFloatingBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.CFLOAT)

class W_Complex128Box(ComplexBox, W_ComplexFloatingBox):
    descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.CDOUBLE)

if long_double_size in (8, 12, 16):
    class W_FloatLongBox(W_FloatingBox, PrimitiveBox):
        descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.LONGDOUBLE)

    class W_ComplexLongBox(ComplexBox, W_ComplexFloatingBox):
        descr__new__, _get_dtype, descr_reduce = new_dtype_getter(NPY.CLONGDOUBLE)

class W_FlexibleBox(W_GenericBox):
    _attrs_ = ['arr', 'ofs', 'dtype']
    _immutable_fields_ = ['arr', 'ofs', 'dtype']

    def __init__(self, arr, ofs, dtype):
        self.arr = arr # we have to keep array alive
        self.ofs = ofs
        self.dtype = dtype

    def get_dtype(self, space):
        return self.dtype

    def raw_str(self):
        return self.arr.dtype.itemtype.to_str(self)

class W_VoidBox(W_FlexibleBox):
    def descr_getitem(self, space, w_item):
        if space.isinstance_w(w_item, space.w_basestring):
            item = space.str_w(w_item)
        elif space.isinstance_w(w_item, space.w_int):
            indx = space.int_w(w_item)
            try:
                item = self.dtype.names[indx]
            except IndexError:
                if indx < 0:
                    indx += len(self.dtype.names)
                raise OperationError(space.w_IndexError, space.wrap(
                    "invalid index (%d)" % indx))
        else:
            raise OperationError(space.w_IndexError, space.wrap(
                "invalid index"))
        try:
            ofs, dtype = self.dtype.fields[item]
        except KeyError:
            raise OperationError(space.w_IndexError, space.wrap(
                "invalid index"))

        from pypy.module.micronumpy.types import VoidType
        if isinstance(dtype.itemtype, VoidType):
            read_val = dtype.itemtype.readarray(self.arr, self.ofs, ofs, dtype)
        else:
            read_val = dtype.itemtype.read(self.arr, self.ofs, ofs, dtype)
        if isinstance (read_val, W_StringBox):
            # StringType returns a str
            return space.wrap(dtype.itemtype.to_str(read_val))
        return read_val

    def descr_setitem(self, space, w_item, w_value):
        if space.isinstance_w(w_item, space.w_basestring):
            item = space.str_w(w_item)
        else:
            raise OperationError(space.w_IndexError, space.wrap(
                "invalid index"))
        try:
            ofs, dtype = self.dtype.fields[item]
        except KeyError:
            raise OperationError(space.w_ValueError,
                                 space.wrap("field named %s not found" % item))
        dtype.itemtype.store(self.arr, self.ofs, ofs,
                             dtype.coerce(space, w_value))

    def convert_to(self, space, dtype):
        # if we reach here, the record fields are guarenteed to match.
        return self

class W_CharacterBox(W_FlexibleBox):
    def convert_to(self, space, dtype):
        return dtype.coerce(space, space.wrap(self.raw_str()))

    def descr_len(self, space):
        return space.len(self.item(space))

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

        arg = space.unicode_w(space.unicode_from_object(w_arg))
        # XXX size computations, we need tests anyway
        arr = VoidBoxStorage(len(arg), new_unicode_dtype(space, len(arg)))
        # XXX not this way, we need store
        #for i in range(len(arg)):
        #    arr.storage[i] = arg[i]
        return W_UnicodeBox(arr, 0, arr.dtype)

W_GenericBox.typedef = TypeDef("generic",
    __module__ = "numpy",

    __new__ = interp2app(W_GenericBox.descr__new__.im_func),

    __getitem__ = interp2app(W_GenericBox.descr_getitem),
    __str__ = interp2app(W_GenericBox.descr_str),
    __repr__ = interp2app(W_GenericBox.descr_str),
    __format__ = interp2app(W_GenericBox.descr_format),
    __int__ = interp2app(W_GenericBox.descr_int),
    __long__ = interp2app(W_GenericBox.descr_long),
    __float__ = interp2app(W_GenericBox.descr_float),
    __nonzero__ = interp2app(W_GenericBox.descr_nonzero),
    __oct__ = interp2app(W_GenericBox.descr_oct),
    __hex__ = interp2app(W_GenericBox.descr_hex),
    __buffer__ = interp2app(W_GenericBox.descr_buffer),

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
    min = interp2app(W_GenericBox.descr_self),
    max = interp2app(W_GenericBox.descr_self),
    argmin = interp2app(W_GenericBox.descr_zero),
    argmax = interp2app(W_GenericBox.descr_zero),
    sum = interp2app(W_GenericBox.descr_self),
    prod = interp2app(W_GenericBox.descr_self),
    any = interp2app(W_GenericBox.descr_any),
    all = interp2app(W_GenericBox.descr_all),
    ravel = interp2app(W_GenericBox.descr_ravel),
    round = interp2app(W_GenericBox.descr_round),
    conjugate = interp2app(W_GenericBox.descr_conjugate),
    astype = interp2app(W_GenericBox.descr_astype),
    view = interp2app(W_GenericBox.descr_view),
    squeeze = interp2app(W_GenericBox.descr_self),
    copy = interp2app(W_GenericBox.descr_copy),
    byteswap = interp2app(W_GenericBox.descr_byteswap),
    tostring = interp2app(W_GenericBox.descr_tostring),
    reshape = interp2app(W_GenericBox.descr_reshape),

    dtype = GetSetProperty(W_GenericBox.descr_get_dtype),
    size = GetSetProperty(W_GenericBox.descr_get_size),
    itemsize = GetSetProperty(W_GenericBox.descr_get_itemsize),
    nbytes = GetSetProperty(W_GenericBox.descr_get_itemsize),
    shape = GetSetProperty(W_GenericBox.descr_get_shape),
    strides = GetSetProperty(W_GenericBox.descr_get_shape),
    ndim = GetSetProperty(W_GenericBox.descr_get_ndim),
    T = GetSetProperty(W_GenericBox.descr_self),
    real = GetSetProperty(W_GenericBox.descr_get_real),
    imag = GetSetProperty(W_GenericBox.descr_get_imag),
    flags = GetSetProperty(W_GenericBox.descr_get_flags),
)

W_BoolBox.typedef = TypeDef("bool_", W_GenericBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_BoolBox.descr__new__.im_func),
    __index__ = interp2app(W_BoolBox.descr_index),
    __reduce__ = interp2app(W_BoolBox.descr_reduce),
)

W_NumberBox.typedef = TypeDef("number", W_GenericBox.typedef,
    __module__ = "numpy",
)

W_IntegerBox.typedef = TypeDef("integer", W_NumberBox.typedef,
    __module__ = "numpy",
)

W_SignedIntegerBox.typedef = TypeDef("signedinteger", W_IntegerBox.typedef,
    __module__ = "numpy",
)

W_UnsignedIntegerBox.typedef = TypeDef("unsignedinteger", W_IntegerBox.typedef,
    __module__ = "numpy",
)

W_Int8Box.typedef = TypeDef("int8", W_SignedIntegerBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_Int8Box.descr__new__.im_func),
    __index__ = interp2app(W_Int8Box.descr_index),
    __reduce__ = interp2app(W_Int8Box.descr_reduce),
)

W_UInt8Box.typedef = TypeDef("uint8", W_UnsignedIntegerBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_UInt8Box.descr__new__.im_func),
    __index__ = interp2app(W_UInt8Box.descr_index),
    __reduce__ = interp2app(W_UInt8Box.descr_reduce),
)

W_Int16Box.typedef = TypeDef("int16", W_SignedIntegerBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_Int16Box.descr__new__.im_func),
    __index__ = interp2app(W_Int16Box.descr_index),
    __reduce__ = interp2app(W_Int16Box.descr_reduce),
)

W_UInt16Box.typedef = TypeDef("uint16", W_UnsignedIntegerBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_UInt16Box.descr__new__.im_func),
    __index__ = interp2app(W_UInt16Box.descr_index),
    __reduce__ = interp2app(W_UInt16Box.descr_reduce),
)

W_Int32Box.typedef = TypeDef("int32", (W_SignedIntegerBox.typedef,) + MIXIN_32,
    __module__ = "numpy",
    __new__ = interp2app(W_Int32Box.descr__new__.im_func),
    __index__ = interp2app(W_Int32Box.descr_index),
    __reduce__ = interp2app(W_Int32Box.descr_reduce),
)

W_UInt32Box.typedef = TypeDef("uint32", W_UnsignedIntegerBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_UInt32Box.descr__new__.im_func),
    __index__ = interp2app(W_UInt32Box.descr_index),
    __reduce__ = interp2app(W_UInt32Box.descr_reduce),
)

W_Int64Box.typedef = TypeDef("int64", (W_SignedIntegerBox.typedef,) + MIXIN_64,
    __module__ = "numpy",
    __new__ = interp2app(W_Int64Box.descr__new__.im_func),
    __index__ = interp2app(W_Int64Box.descr_index),
    __reduce__ = interp2app(W_Int64Box.descr_reduce),
)

W_UInt64Box.typedef = TypeDef("uint64", W_UnsignedIntegerBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_UInt64Box.descr__new__.im_func),
    __index__ = interp2app(W_UInt64Box.descr_index),
    __reduce__ = interp2app(W_UInt64Box.descr_reduce),
)

W_LongBox.typedef = TypeDef("int%d" % LONG_BIT,
    (W_SignedIntegerBox.typedef, W_IntObject.typedef),
    __module__ = "numpy",
    __new__ = interp2app(W_LongBox.descr__new__.im_func),
    __index__ = interp2app(W_LongBox.descr_index),
    __reduce__ = interp2app(W_LongBox.descr_reduce),
)

W_ULongBox.typedef = TypeDef("uint%d" % LONG_BIT, W_UnsignedIntegerBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_ULongBox.descr__new__.im_func),
    __index__ = interp2app(W_ULongBox.descr_index),
    __reduce__ = interp2app(W_ULongBox.descr_reduce),
)

W_InexactBox.typedef = TypeDef("inexact", W_NumberBox.typedef,
    __module__ = "numpy",
)

W_FloatingBox.typedef = TypeDef("floating", W_InexactBox.typedef,
    __module__ = "numpy",
)

W_Float16Box.typedef = TypeDef("float16", W_FloatingBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_Float16Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Float16Box.descr_reduce),
)

W_Float32Box.typedef = TypeDef("float32", W_FloatingBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_Float32Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Float32Box.descr_reduce),
)

W_Float64Box.typedef = TypeDef("float64", (W_FloatingBox.typedef, float_typedef),
    __module__ = "numpy",
    __new__ = interp2app(W_Float64Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Float64Box.descr_reduce),
    as_integer_ratio = interp2app(W_Float64Box.descr_as_integer_ratio),
)

W_ComplexFloatingBox.typedef = TypeDef("complexfloating", W_InexactBox.typedef,
    __module__ = "numpy",
)

W_Complex64Box.typedef = TypeDef("complex64", (W_ComplexFloatingBox.typedef),
    __module__ = "numpy",
    __new__ = interp2app(W_Complex64Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Complex64Box.descr_reduce),
    __complex__ = interp2app(W_GenericBox.item),
)

W_Complex128Box.typedef = TypeDef("complex128", (W_ComplexFloatingBox.typedef, complex_typedef),
    __module__ = "numpy",
    __new__ = interp2app(W_Complex128Box.descr__new__.im_func),
    __reduce__ = interp2app(W_Complex128Box.descr_reduce),
)

if long_double_size in (8, 12, 16):
    W_FloatLongBox.typedef = TypeDef("float%d" % (long_double_size * 8), (W_FloatingBox.typedef),
        __module__ = "numpy",
        __new__ = interp2app(W_FloatLongBox.descr__new__.im_func),
        __reduce__ = interp2app(W_FloatLongBox.descr_reduce),
    )

    W_ComplexLongBox.typedef = TypeDef("complex%d" % (long_double_size * 16), (W_ComplexFloatingBox.typedef, complex_typedef),
        __module__ = "numpy",
        __new__ = interp2app(W_ComplexLongBox.descr__new__.im_func),
        __reduce__ = interp2app(W_ComplexLongBox.descr_reduce),
        __complex__ = interp2app(W_GenericBox.item),
    )

W_FlexibleBox.typedef = TypeDef("flexible", W_GenericBox.typedef,
    __module__ = "numpy",
)

W_VoidBox.typedef = TypeDef("void", W_FlexibleBox.typedef,
    __module__ = "numpy",
    __new__ = interp2app(W_VoidBox.descr__new__.im_func),
    __getitem__ = interp2app(W_VoidBox.descr_getitem),
    __setitem__ = interp2app(W_VoidBox.descr_setitem),
)

W_CharacterBox.typedef = TypeDef("character", W_FlexibleBox.typedef,
    __module__ = "numpy",
)

W_StringBox.typedef = TypeDef("string_", (W_CharacterBox.typedef, W_BytesObject.typedef),
    __module__ = "numpy",
    __new__ = interp2app(W_StringBox.descr__new__string_box.im_func),
    __len__ = interp2app(W_StringBox.descr_len),
)

W_UnicodeBox.typedef = TypeDef("unicode_", (W_CharacterBox.typedef, W_UnicodeObject.typedef),
    __module__ = "numpy",
    __new__ = interp2app(W_UnicodeBox.descr__new__unicode_box.im_func),
    __len__ = interp2app(W_UnicodeBox.descr_len),
)
