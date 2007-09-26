
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import ovfcheck

from pypy.module.struct.error import StructError
from pypy.module.struct.standardfmttable import standard_fmttable
from pypy.module.struct.nativefmttable import native_is_bigendian


class FormatIterator(object):
    """
    An iterator-like object that follows format strings step by step.
    It provides input to the packer/unpacker and accumulates their output.
    The subclasses are specialized for either packing, unpacking, or
    just computing the size.
    """
    _mixin_ = True

    def interpret(self, fmt):
        # decode the byte order, size and alignment based on the 1st char
        native = True
        bigendian = native_is_bigendian
        index = 0
        if len(fmt) > 0:
            c = fmt[0]
            index = 1
            if c == '@':
                pass
            elif c == '=':
                native = False
            elif c == '<':
                native = False
                bigendian = False
            elif c == '>' or c == '!':
                native = False
                bigendian = True
            else:
                index = 0
        self.native = native
        self.bigendian = bigendian
        # interpret the format string,
        # calling self.operate() for each format unit
        while index < len(fmt):
            c = fmt[index]
            index += 1
            if c.isspace():
                continue
            if c.isdigit():
                repetitions = ord(c) - ord('0')
                while True:
                    if index == len(fmt):
                        raise StructError("incomplete struct format")
                    c = fmt[index]
                    index += 1
                    if not c.isdigit():
                        break
                    repetitions = ovfcheck(repetitions * 10)
                    repetitions = ovfcheck(repetitions + (ord(c) - ord('0')))
                    # XXX catch OverflowError somewhere
            else:
                repetitions = 1

            for fmtop in unroll_fmtops:
                if c == fmtop.fmtchar:
                    self.operate(fmtop, repetitions)
                    break
            else:
                raise StructError("bad char in struct format")


class CalcSizeFormatIterator(FormatIterator):
    totalsize = 0

    def operate(self, fmtop, repetitions):
        if fmtop.size == 1:
            size = repetitions  # skip the overflow-checked multiplication by 1
        else:
            size = ovfcheck(fmtop.size * repetitions)
        self.totalsize = ovfcheck(self.totalsize + size)
    operate._annspecialcase_ = 'specialize:argvalue(1)'


class PackFormatIterator(FormatIterator):

    def __init__(self, space, args_w):
        self.space = space
        self.args_iterator = iter(args_w)
        self.result = []      # list of characters

    def operate(self, fmtop, repetitions):
        # XXX 's', 'p'
        for i in range(repetitions):
            fmtop.pack(self)
    operate._annspecialcase_ = 'specialize:argvalue(1)'

    def accept_int_arg(self):
        w_obj = self.args_iterator.next()   # XXX catch StopIteration
        return self.space.int_w(w_obj)


class UnpackFormatIterator(FormatIterator):

    def __init__(self, space, input):
        self.space = space
        self.input = input
        self.inputpos = 0
        self.result_w = []     # list of wrapped objects

    def operate(self, fmtop, repetitions):
        # XXX 's', 'p'
        for i in range(repetitions):
            fmtop.unpack(self)
    operate._annspecialcase_ = 'specialize:argvalue(1)'

    def read(self, count):
        end = self.inputpos + count
        if end > len(self.input):
            raise StructError("unpack str size is too short for the format")
        s = self.input[self.inputpos : end]
        self.inputpos = end
        return s

    def append(self, value):
        self.result_w.append(self.space.wrap(value))
    append._annspecialcase_ = 'specialize:argtype(1)'


class FmtOp(object):
    def __init__(self, fmtchar, attrs):
        self.fmtchar = fmtchar
        self.__dict__.update(attrs)
    def _freeze_(self):
        return True

_items = standard_fmttable.items()
_items.sort()
unroll_fmtops = unrolling_iterable([FmtOp(_key, _attrs)
                                    for _key, _attrs in _items])
