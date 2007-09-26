from pypy.interpreter.gateway import ObjSpace
from pypy.module.struct.formatiterator import CalcSizeFormatIterator


def calcsize(space, format):
    fmtiter = CalcSizeFormatIterator(format)
    return space.wrap(fmtiter.totalsize)
calcsize.unwrap_spec = [ObjSpace, str]
