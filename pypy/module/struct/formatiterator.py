
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.rarithmetic import ovfcheck

from pypy.module.struct.error import StructError
from pypy.module.struct.standardfmttable import standard_fmttable
from pypy.module.struct.nativefmttable import native_fmttable
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
        table = unroll_native_fmtdescs
        self.bigendian = native_is_bigendian
        index = 0
        if len(fmt) > 0:
            c = fmt[0]
            index = 1
            if c == '@':
                pass
            elif c == '=':
                table = unroll_standard_fmtdescs
            elif c == '<':
                table = unroll_standard_fmtdescs
                self.bigendian = False
            elif c == '>' or c == '!':
                table = unroll_standard_fmtdescs
                self.bigendian = True
            else:
                index = 0

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
                    try:
                        repetitions = ovfcheck(repetitions * 10)
                        repetitions = ovfcheck(repetitions + (ord(c) -
                                                              ord('0')))
                    except OverflowError:
                        raise StructError("overflow in item count")
                assert repetitions >= 0
            else:
                repetitions = 1

            for fmtdesc in table:
                if c == fmtdesc.fmtchar:
                    if fmtdesc.alignment > 1:
                        self.align(fmtdesc.mask)
                    self.operate(fmtdesc, repetitions)
                    break
            else:
                raise StructError("bad char in struct format")
        self.finished()

    def finished(self):
        pass


class CalcSizeFormatIterator(FormatIterator):
    totalsize = 0

    def operate(self, fmtdesc, repetitions):
        try:
            if fmtdesc.size == 1:
                # skip the overflow-checked multiplication by 1
                size = repetitions
            else:
                size = ovfcheck(fmtdesc.size * repetitions)
            self.totalsize = ovfcheck(self.totalsize + size)
        except OverflowError:
            raise StructError("total struct size too long")
    operate._annspecialcase_ = 'specialize:arg(1)'

    def align(self, mask):
        pad = (-self.totalsize) & mask
        try:
            self.totalsize = ovfcheck(self.totalsize + pad)
        except OverflowError:
            raise StructError("total struct size too long")


class PackFormatIterator(FormatIterator):

    def __init__(self, space, args_w):
        self.space = space
        self.args_w = args_w
        self.args_index = 0
        self.result = []      # list of characters

    def operate(self, fmtdesc, repetitions):
        if fmtdesc.needcount:
            fmtdesc.pack(self, repetitions)
        else:
            for i in range(repetitions):
                fmtdesc.pack(self)
    operate._annspecialcase_ = 'specialize:arg(1)'

    def align(self, mask):
        pad = (-len(self.result)) & mask
        for i in range(pad):
            self.result.append('\x00')

    def finished(self):
        if self.args_index != len(self.args_w):
            raise StructError("too many arguments for struct format")

    def accept_obj_arg(self):
        try:
            w_obj = self.args_w[self.args_index]
        except IndexError:
            raise StructError("struct format requires more arguments")
        self.args_index += 1
        return w_obj

    def accept_int_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.int_w(w_obj)

    def accept_uint_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.uint_w(w_obj)

    def accept_longlong_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.r_longlong_w(w_obj)

    def accept_ulonglong_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.r_ulonglong_w(w_obj)

    def accept_str_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.str_w(w_obj)

    def accept_float_arg(self):
        w_obj = self.accept_obj_arg()
        return self.space.float_w(w_obj)


class UnpackFormatIterator(FormatIterator):

    def __init__(self, space, input):
        self.space = space
        self.input = input
        self.inputpos = 0
        self.result_w = []     # list of wrapped objects

    def operate(self, fmtdesc, repetitions):
        if fmtdesc.needcount:
            fmtdesc.unpack(self, repetitions)
        else:
            for i in range(repetitions):
                fmtdesc.unpack(self)
    operate._annspecialcase_ = 'specialize:arg(1)'

    def align(self, mask):
        self.inputpos = (self.inputpos + mask) & ~mask

    def finished(self):
        if self.inputpos != len(self.input):
            raise StructError("unpack str size too long for format")

    def read(self, count):
        end = self.inputpos + count
        if end > len(self.input):
            raise StructError("unpack str size too short for format")
        s = self.input[self.inputpos : end]
        self.inputpos = end
        return s

    def appendobj(self, value):
        self.result_w.append(self.space.wrap(value))
    appendobj._annspecialcase_ = 'specialize:argtype(1)'


class FmtDesc(object):
    def __init__(self, fmtchar, attrs):
        self.fmtchar = fmtchar
        self.alignment = 1      # by default
        self.needcount = False  # by default
        self.__dict__.update(attrs)
        self.mask = self.alignment - 1
        assert self.alignment & self.mask == 0, (
            "this module assumes that all alignments are powers of two")
    def _freeze_(self):
        return True

def table2desclist(table):
    items = table.items()
    items.sort()
    lst = [FmtDesc(key, attrs) for key, attrs in items]
    return unrolling_iterable(lst)

unroll_standard_fmtdescs = table2desclist(standard_fmttable)
unroll_native_fmtdescs   = table2desclist(native_fmttable)
