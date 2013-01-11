from pypy.interpreter.gateway import unwrap_spec
from pypy.interpreter.error import OperationError
from pypy.module.struct.formatiterator import PackFormatIterator, UnpackFormatIterator
from rpython.rlib import jit
from rpython.rlib.rstruct.error import StructError, StructOverflowError
from rpython.rlib.rstruct.formatiterator import CalcSizeFormatIterator


@unwrap_spec(format=str)
def calcsize(space, format):
    return space.wrap(_calcsize(space, format))

def _calcsize(space, format):
    fmtiter = CalcSizeFormatIterator()
    try:
        fmtiter.interpret(format)
    except StructOverflowError, e:
        raise OperationError(space.w_OverflowError, space.wrap(self.msg))
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
        raise OperationError(space.w_OverflowError, space.wrap(self.msg))
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
        raise OperationError(space.w_OverflowError, space.wrap(self.msg))
    except StructError, e:
        w_module = space.getbuiltinmodule('struct')
        w_error = space.getattr(w_module, space.wrap('error'))
        raise OperationError(w_error, space.wrap(e.msg))
    return space.newtuple(fmtiter.result_w[:])
