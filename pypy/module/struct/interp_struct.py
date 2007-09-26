from pypy.interpreter.gateway import ObjSpace
from pypy.module.struct.formatiterator import CalcSizeFormatIterator
from pypy.module.struct.formatiterator import PackFormatIterator


def calcsize(space, format):
    fmtiter = CalcSizeFormatIterator()
    fmtiter.interpret(format)
    return space.wrap(fmtiter.totalsize)
calcsize.unwrap_spec = [ObjSpace, str]


def pack(space, format, args_w):
    fmtiter = PackFormatIterator(space, args_w)
    fmtiter.interpret(format)
    result = ''.join(fmtiter.result)
    return space.wrap(result)
pack.unwrap_spec = [ObjSpace, str, 'args_w']
