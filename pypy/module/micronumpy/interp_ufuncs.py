from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
from pypy.module.micronumpy import interp_dtype, signature
from pypy.rlib import jit
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.tool.sourcetools import func_with_new_name


reduce_driver = jit.JitDriver(
    greens = ["signature"],
    reds = ["i", "size", "self", "dtype", "value", "obj"]
)

class W_Ufunc(Wrappable):
    _attrs_ = ["name", "promote_to_float", "promote_bools", "identity"]

    def __init__(self, name, promote_to_float, promote_bools, identity):
        self.name = name
        self.promote_to_float = promote_to_float
        self.promote_bools = promote_bools

        self.identity = identity

    def descr_repr(self, space):
        return space.wrap("<ufunc '%s'>" % self.name)

    def descr_get_identity(self, space):
        if self.identity is None:
            return space.w_None
        return self.identity.wrap(space)

    def descr_call(self, space, __args__):
        try:
            args_w = __args__.fixedunpack(self.argcount)
        except ValueError, e:
            raise OperationError(space.w_TypeError, space.wrap(str(e)))
        return self.call(space, args_w)

    def descr_reduce(self, space, w_obj):
        from pypy.module.micronumpy.interp_numarray import convert_to_array, Scalar

        if self.argcount != 2:
            raise OperationError(space.w_ValueError, space.wrap("reduce only "
                "supported for binary functions"))

        assert isinstance(self, W_Ufunc2)
        obj = convert_to_array(space, w_obj)
        if isinstance(obj, Scalar):
            raise OperationError(space.w_TypeError, space.wrap("cannot reduce "
                "on a scalar"))

        size = obj.find_size()
        dtype = find_unaryop_result_dtype(
            space, obj.find_dtype(),
            promote_to_largest=True
        )
        start = 0
        if self.identity is None:
            if size == 0:
                raise operationerrfmt(space.w_ValueError, "zero-size array to "
                    "%s.reduce without identity", self.name)
            value = obj.eval(0).convert_to(dtype)
            start += 1
        else:
            value = self.identity.convert_to(dtype)
        new_sig = signature.Signature.find_sig([
            self.reduce_signature, obj.signature
        ])
        return self.reduce(new_sig, start, value, obj, dtype, size).wrap(space)

    def reduce(self, signature, start, value, obj, dtype, size):
        i = start
        while i < size:
            reduce_driver.jit_merge_point(signature=signature, self=self,
                                          value=value, obj=obj, i=i,
                                          dtype=dtype, size=size)
            value = self.func(dtype, value, obj.eval(i).convert_to(dtype))
            i += 1
        return value

class W_Ufunc1(W_Ufunc):
    argcount = 1

    def __init__(self, func, name, promote_to_float=False, promote_bools=False,
        identity=None):

        W_Ufunc.__init__(self, name, promote_to_float, promote_bools, identity)
        self.func = func
        self.signature = signature.Call1(func)

    def call(self, space, args_w):
        from pypy.module.micronumpy.interp_numarray import (Call1,
            convert_to_array, Scalar)

        [w_obj] = args_w
        w_obj = convert_to_array(space, w_obj)
        res_dtype = find_unaryop_result_dtype(space,
            w_obj.find_dtype(),
            promote_to_float=self.promote_to_float,
            promote_bools=self.promote_bools,
        )
        if isinstance(w_obj, Scalar):
            return self.func(res_dtype, w_obj.value.convert_to(res_dtype)).wrap(space)

        new_sig = signature.Signature.find_sig([self.signature, w_obj.signature])
        w_res = Call1(new_sig, w_obj.shape, res_dtype, w_obj)
        w_obj.add_invalidates(w_res)
        return w_res


class W_Ufunc2(W_Ufunc):
    argcount = 2

    def __init__(self, func, name, promote_to_float=False, promote_bools=False,
        identity=None, comparison_func=False):

        W_Ufunc.__init__(self, name, promote_to_float, promote_bools, identity)
        self.func = func
        self.comparison_func = comparison_func
        self.signature = signature.Call2(func)
        self.reduce_signature = signature.BaseSignature()

    def call(self, space, args_w):
        from pypy.module.micronumpy.interp_numarray import (Call2,
            convert_to_array, Scalar)

        [w_lhs, w_rhs] = args_w
        w_lhs = convert_to_array(space, w_lhs)
        w_rhs = convert_to_array(space, w_rhs)
        calc_dtype = find_binop_result_dtype(space,
            w_lhs.find_dtype(), w_rhs.find_dtype(),
            promote_to_float=self.promote_to_float,
            promote_bools=self.promote_bools,
        )
        if self.comparison_func:
            res_dtype = space.fromcache(interp_dtype.W_BoolDtype)
        else:
            res_dtype = calc_dtype
        if isinstance(w_lhs, Scalar) and isinstance(w_rhs, Scalar):
            return self.func(calc_dtype,
                w_lhs.value.convert_to(calc_dtype),
                w_rhs.value.convert_to(calc_dtype)
            ).wrap(space)

        new_sig = signature.Signature.find_sig([
            self.signature, w_lhs.signature, w_rhs.signature
        ])
        w_res = Call2(new_sig, w_lhs.shape or w_rhs.shape, calc_dtype,
                      res_dtype, w_lhs, w_rhs)
        w_lhs.add_invalidates(w_res)
        w_rhs.add_invalidates(w_res)
        return w_res


W_Ufunc.typedef = TypeDef("ufunc",
    __module__ = "numpy",

    __call__ = interp2app(W_Ufunc.descr_call),
    __repr__ = interp2app(W_Ufunc.descr_repr),

    identity = GetSetProperty(W_Ufunc.descr_get_identity),
    nin = interp_attrproperty("argcount", cls=W_Ufunc),

    reduce = interp2app(W_Ufunc.descr_reduce),
)

def find_binop_result_dtype(space, dt1, dt2, promote_to_float=False,
    promote_bools=False):
    # dt1.num should be <= dt2.num
    if dt1.num > dt2.num:
        dt1, dt2 = dt2, dt1
    # Some operations promote op(bool, bool) to return int8, rather than bool
    if promote_bools and (dt1.kind == dt2.kind == interp_dtype.BOOLLTR):
        return space.fromcache(interp_dtype.W_Int8Dtype)
    if promote_to_float:
        return find_unaryop_result_dtype(space, dt2, promote_to_float=True)
    # If they're the same kind, choose the greater one.
    if dt1.kind == dt2.kind:
        return dt2

    # Everything promotes to float, and bool promotes to everything.
    if dt2.kind == interp_dtype.FLOATINGLTR or dt1.kind == interp_dtype.BOOLLTR:
        # Float32 + 8-bit int = Float64
        if dt2.num == 11 and dt1.num_bytes >= 4:
            return space.fromcache(interp_dtype.W_Float64Dtype)
        return dt2

    # for now this means mixing signed and unsigned
    if dt2.kind == interp_dtype.SIGNEDLTR:
        # if dt2 has a greater number of bytes, then just go with it
        if dt1.num_bytes < dt2.num_bytes:
            return dt2
        # we need to promote both dtypes
        dtypenum = dt2.num + 2
    else:
        # increase to the next signed type (or to float)
        dtypenum = dt2.num + 1
        # UInt64 + signed = Float64
        if dt2.num == 10:
            dtypenum += 1
    newdtype = interp_dtype.ALL_DTYPES[dtypenum]

    if newdtype.num_bytes > dt2.num_bytes or newdtype.kind == interp_dtype.FLOATINGLTR:
        return space.fromcache(newdtype)
    else:
        # we only promoted to long on 32-bit or to longlong on 64-bit
        # this is really for dealing with the Long and Ulong dtypes
        if LONG_BIT == 32:
            dtypenum += 2
        else:
            dtypenum += 3
        return space.fromcache(interp_dtype.ALL_DTYPES[dtypenum])

def find_unaryop_result_dtype(space, dt, promote_to_float=False,
    promote_bools=False, promote_to_largest=False):
    if promote_bools and (dt.kind == interp_dtype.BOOLLTR):
        return space.fromcache(interp_dtype.W_Int8Dtype)
    if promote_to_float:
        if dt.kind == interp_dtype.FLOATINGLTR:
            return dt
        if dt.num >= 5:
            return space.fromcache(interp_dtype.W_Float64Dtype)
        for bytes, dtype in interp_dtype.dtypes_by_num_bytes:
            if dtype.kind == interp_dtype.FLOATINGLTR and dtype.num_bytes > dt.num_bytes:
                return space.fromcache(dtype)
    if promote_to_largest:
        if dt.kind == interp_dtype.BOOLLTR or dt.kind == interp_dtype.SIGNEDLTR:
            return space.fromcache(interp_dtype.W_Int64Dtype)
        elif dt.kind == interp_dtype.FLOATINGLTR:
            return space.fromcache(interp_dtype.W_Float64Dtype)
        elif dt.kind == interp_dtype.UNSIGNEDLTR:
            return space.fromcache(interp_dtype.W_UInt64Dtype)
        else:
            assert False
    return dt

def find_dtype_for_scalar(space, w_obj, current_guess=None):
    bool_dtype = space.fromcache(interp_dtype.W_BoolDtype)
    long_dtype = space.fromcache(interp_dtype.W_LongDtype)
    int64_dtype = space.fromcache(interp_dtype.W_Int64Dtype)

    if space.isinstance_w(w_obj, space.w_bool):
        if current_guess is None or current_guess is bool_dtype:
            return bool_dtype
        return current_guess
    elif space.isinstance_w(w_obj, space.w_int):
        if (current_guess is None or current_guess is bool_dtype or
            current_guess is long_dtype):
            return long_dtype
        return current_guess
    elif space.isinstance_w(w_obj, space.w_long):
        if (current_guess is None or current_guess is bool_dtype or
            current_guess is long_dtype or current_guess is int64_dtype):
            return int64_dtype
        return current_guess
    return space.fromcache(interp_dtype.W_Float64Dtype)


def ufunc_dtype_caller(space, ufunc_name, op_name, argcount, comparison_func):
    if argcount == 1:
        def impl(res_dtype, value):
            return getattr(res_dtype, op_name)(value)
    elif argcount == 2:
        def impl(res_dtype, lvalue, rvalue):
            res = getattr(res_dtype, op_name)(lvalue, rvalue)
            if comparison_func:
                booldtype = space.fromcache(interp_dtype.W_BoolDtype)
                assert isinstance(booldtype, interp_dtype.W_BoolDtype)
                res = booldtype.box(res)
            return res
    return func_with_new_name(impl, ufunc_name)

class UfuncState(object):
    def __init__(self, space):
        "NOT_RPYTHON"
        for ufunc_def in [
            ("add", "add", 2, {"identity": 0}),
            ("subtract", "sub", 2),
            ("multiply", "mul", 2, {"identity": 1}),
            ("divide", "div", 2, {"promote_bools": True}),
            ("mod", "mod", 2, {"promote_bools": True}),
            ("power", "pow", 2, {"promote_bools": True}),

            ("equal", "eq", 2, {"comparison_func": True}),
            ("not_equal", "ne", 2, {"comparison_func": True}),
            ("less", "lt", 2, {"comparison_func": True}),
            ("less_equal", "le", 2, {"comparison_func": True}),
            ("greater", "gt", 2, {"comparison_func": True}),
            ("greater_equal", "ge", 2, {"comparison_func": True}),

            ("maximum", "max", 2),
            ("minimum", "min", 2),

            ("copysign", "copysign", 2, {"promote_to_float": True}),

            ("positive", "pos", 1),
            ("negative", "neg", 1),
            ("absolute", "abs", 1),
            ("sign", "sign", 1, {"promote_bools": True}),
            ("reciprocal", "reciprocal", 1),

            ("fabs", "fabs", 1, {"promote_to_float": True}),
            ("floor", "floor", 1, {"promote_to_float": True}),
            ("exp", "exp", 1, {"promote_to_float": True}),

            ("sin", "sin", 1, {"promote_to_float": True}),
            ("cos", "cos", 1, {"promote_to_float": True}),
            ("tan", "tan", 1, {"promote_to_float": True}),
            ("arcsin", "arcsin", 1, {"promote_to_float": True}),
            ("arccos", "arccos", 1, {"promote_to_float": True}),
            ("arctan", "arctan", 1, {"promote_to_float": True}),
            ("arcsinh", "arcsinh", 1, {"promote_to_float": True}),
            ("arctanh", "arctanh", 1, {"promote_to_float": True}),
        ]:
            self.add_ufunc(space, *ufunc_def)

    def add_ufunc(self, space, ufunc_name, op_name, argcount, extra_kwargs=None):
        if extra_kwargs is None:
            extra_kwargs = {}

        identity = extra_kwargs.get("identity")
        if identity is not None:
            identity = space.fromcache(interp_dtype.W_LongDtype).adapt_val(identity)
        extra_kwargs["identity"] = identity

        func = ufunc_dtype_caller(space, ufunc_name, op_name, argcount,
            comparison_func=extra_kwargs.get("comparison_func", False)
        )
        if argcount == 1:
            ufunc = W_Ufunc1(func, ufunc_name, **extra_kwargs)
        elif argcount == 2:
            ufunc = W_Ufunc2(func, ufunc_name, **extra_kwargs)
        setattr(self, ufunc_name, ufunc)

def get(space):
    return space.fromcache(UfuncState)
