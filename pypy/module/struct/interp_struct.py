from pypy.interpreter.gateway import unwrap_spec
from pypy.rlib.rstruct.error import StructError
from pypy.module.struct.formatiterator import (CalcSizeFormatIterator,
    PackFormatIterator, UnpackFormatIterator)


@unwrap_spec(format=str)
def calcsize(space, format):
    fmtiter = CalcSizeFormatIterator()
    try:
        fmtiter.interpret(format)
    except StructError, e:
        raise e.at_applevel(space)
    return space.wrap(fmtiter.totalsize)


@unwrap_spec(format=str)
def pack(space, format, args_w):
    fmtiter = PackFormatIterator(space, args_w)
    try:
        fmtiter.interpret(format)
    except StructError, e:
        raise e.at_applevel(space)
    result = ''.join(fmtiter.result)
    return space.wrap(result)


@unwrap_spec(format=str, input='bufferstr')
def unpack(space, format, input):
    fmtiter = UnpackFormatIterator(space, input)
    try:
        fmtiter.interpret(format)
    except StructError, e:
        raise e.at_applevel(space)
    return space.newtuple(fmtiter.result_w[:])
