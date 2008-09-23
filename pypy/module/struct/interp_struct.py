from pypy.interpreter.gateway import ObjSpace
from pypy.interpreter.error import OperationError
from pypy.rlib.rstruct.error import StructError
from pypy.module.struct.formatiterator import CalcSizeFormatIterator
from pypy.module.struct.formatiterator import PackFormatIterator
from pypy.module.struct.formatiterator import UnpackFormatIterator


def calcsize(space, format):
    fmtiter = CalcSizeFormatIterator()
    try:
        fmtiter.interpret(format)
    except StructError, e:
        raise e.at_applevel(space)
    return space.wrap(fmtiter.totalsize)
calcsize.unwrap_spec = [ObjSpace, str]


def pack(space, format, args_w):
    fmtiter = PackFormatIterator(space, args_w)
    try:
        fmtiter.interpret(format)
    except StructError, e:
        raise e.at_applevel(space)
    result = ''.join(fmtiter.result)
    return space.wrap(result)
pack.unwrap_spec = [ObjSpace, str, 'args_w']


def unpack(space, format, input):
    fmtiter = UnpackFormatIterator(space, input)
    try:
        fmtiter.interpret(format)
    except StructError, e:
        raise e.at_applevel(space)
    return space.newtuple(fmtiter.result_w[:])
unpack.unwrap_spec = [ObjSpace, str, 'bufferstr']
