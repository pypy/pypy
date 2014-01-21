from rpython.rlib import jit
from rpython.rlib.rstruct.error import StructError, StructOverflowError
from rpython.rlib.rstruct.formatiterator import CalcSizeFormatIterator

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import (
    TypeDef, interp_attrproperty, interp_attrproperty_w
)
from pypy.module.struct.formatiterator import (
    PackFormatIterator, UnpackFormatIterator
)


@unwrap_spec(format=str)
def calcsize(space, format):
    return space.wrap(_calcsize(space, format))


def _calcsize(space, format):
    fmtiter = CalcSizeFormatIterator()
    try:
        fmtiter.interpret(format)
    except StructOverflowError, e:
        raise OperationError(space.w_OverflowError, space.wrap(e.msg))
    except StructError, e:
        w_module = space.getbuiltinmodule('struct')
        w_error = space.getattr(w_module, space.wrap('error'))
        raise OperationError(w_error, space.wrap(e.msg))
    return fmtiter.totalsize

@unwrap_spec(format=str)
def pack(space, format, args_w):
    if jit.isconstant(format):
        size = _calcsize(space, format)
    else:
        size = 8
    fmtiter = PackFormatIterator(space, args_w, size)
    try:
        fmtiter.interpret(format)
    except StructOverflowError, e:
        raise OperationError(space.w_OverflowError, space.wrap(e.msg))
    except StructError, e:
        w_module = space.getbuiltinmodule('struct')
        w_error = space.getattr(w_module, space.wrap('error'))
        raise OperationError(w_error, space.wrap(e.msg))
    return space.wrap(fmtiter.result.build())


@unwrap_spec(format=str, input='bufferstr')
def unpack(space, format, input):
    fmtiter = UnpackFormatIterator(space, input)
    try:
        fmtiter.interpret(format)
    except StructOverflowError, e:
        raise OperationError(space.w_OverflowError, space.wrap(e.msg))
    except StructError, e:
        w_module = space.getbuiltinmodule('struct')
        w_error = space.getattr(w_module, space.wrap('error'))
        raise OperationError(w_error, space.wrap(e.msg))
    return space.newtuple(fmtiter.result_w[:])


class W_Struct(W_Root):
    _immutable_fields_ = ["format", "size"]

    def __init__(self, space, format):
        self.format = format
        self.size = _calcsize(space, format)

    @unwrap_spec(format=str)
    def descr__new__(space, w_subtype, format):
        self = space.allocate_instance(W_Struct, w_subtype)
        W_Struct.__init__(self, space, format)
        return self

    def wrap_struct_method(name):
        def impl(self, space, __args__):
            w_module = space.getbuiltinmodule('struct')
            w_method = space.getattr(w_module, space.wrap(name))
            return space.call_obj_args(
                w_method, space.wrap(self.format), __args__
            )

        return impl

    descr_pack = wrap_struct_method("pack")
    descr_unpack = wrap_struct_method("unpack")
    descr_pack_into = wrap_struct_method("pack_into")
    descr_unpack_from = wrap_struct_method("unpack_from")


W_Struct.typedef = TypeDef("Struct",
    __new__=interp2app(W_Struct.descr__new__.im_func),
    format=interp_attrproperty("format", cls=W_Struct),
    size=interp_attrproperty("size", cls=W_Struct),

    pack=interp2app(W_Struct.descr_pack),
    unpack=interp2app(W_Struct.descr_unpack),
    pack_into=interp2app(W_Struct.descr_pack_into),
    unpack_from=interp2app(W_Struct.descr_unpack_from),
)
