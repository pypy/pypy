from pypy.interpreter.gateway import ObjSpace
from pypy.module.struct.formatiterator import CalcSizeFormatIterator
from pypy.module.struct.formatiterator import PackFormatIterator
from pypy.module.struct.formatiterator import UnpackFormatIterator


def calcsize(space, format):
    fmtiter = CalcSizeFormatIterator()
    fmtiter.interpret(format)
    return space.wrap(fmtiter.totalsize)
calcsize.unwrap_spec = [ObjSpace, str]


def pack(space, format, args_w):
    fmtiter = PackFormatIterator(space, args_w)
    fmtiter.interpret(format)
    # XXX check that all arguments have been consumed
    result = ''.join(fmtiter.result)
    return space.wrap(result)
pack.unwrap_spec = [ObjSpace, str, 'args_w']


def unpack(space, format, input):
    fmtiter = UnpackFormatIterator(space, input)
    fmtiter.interpret(format)
    # XXX check that the input string has been fully consumed
    return space.newtuple(fmtiter.result_w)
unpack.unwrap_spec = [ObjSpace, str, str]
