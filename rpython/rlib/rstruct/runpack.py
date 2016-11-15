
""" WARNING! this module is incomplete and may have rough edges. Use only
if necessary
"""

import py
from struct import unpack
from rpython.rlib.rstruct.formatiterator import FormatIterator
from rpython.rlib.rstruct.error import StructError
from rpython.rlib.objectmodel import specialize

class MasterReader(object):
    def __init__(self, s):
        self.input = s
        self.inputpos = 0

    def read(self, count):
        end = self.inputpos + count
        if end > len(self.input):
            raise StructError("unpack str size too short for format")
        s = self.input[self.inputpos : end]
        self.inputpos = end
        return s

    def align(self, mask):
        self.inputpos = (self.inputpos + mask) & ~mask

class AbstractReader(object):
    pass

def reader_for_pos(pos):
    class ReaderForPos(AbstractReader):
        def __init__(self, mr, bigendian):
            self.mr = mr
            self.bigendian = bigendian

        def read(self, count):
            return self.mr.read(count)

        def appendobj(self, value):
            self.value = value

        def get_buffer_as_string_maybe(self):
            return self.mr.input, self.mr.inputpos

        def skip(self, size):
            self.read(size) # XXX, could avoid taking the slice
    ReaderForPos.__name__ = 'ReaderForPos%d' % pos
    return ReaderForPos

class FrozenUnpackIterator(FormatIterator):
    def __init__(self, fmt):
        self.formats = []
        self.fmt = fmt

    def operate(self, fmtdesc, repetitions):
        if fmtdesc.needcount:
            self.formats.append((fmtdesc, repetitions, None))
        else:
            for i in range(repetitions):
                self.formats.append((fmtdesc, 1, None))

    def align(self, mask):
        if self.formats:
            fmt, rep, _ = self.formats.pop()
            self.formats.append((fmt, rep, mask))

    def _create_unpacking_func(self):
        rg = range(len(self.formats))
        perform_lst = []
        miniglobals = {}
        miniglobals.update(globals())
        miniglobals['bigendian'] = self.bigendian
        for i in rg:
            fmtdesc, rep, mask = self.formats[i]
            miniglobals['unpacker%d' % i] = fmtdesc.unpack
            if mask is not None:
                perform_lst.append('master_reader.align(%d)' % mask)
            if not fmtdesc.needcount:
                perform_lst.append('unpacker%d(reader%d)' % (i, i))
            else:
                perform_lst.append('unpacker%d(reader%d, %d)' % (i, i, rep))
            miniglobals['reader_cls%d' % i] = reader_for_pos(i)
        readers = ";".join(["reader%d = reader_cls%d(master_reader, bigendian)"
                            % (i, i) for i in rg])
        perform = ";".join(perform_lst)
        unpackers = ','.join(['reader%d.value' % i for i in rg])
        source = py.code.Source("""
        def unpack(s):
            master_reader = MasterReader(s)
            %(readers)s
            %(perform)s
            return (%(unpackers)s)
        """ % locals())
        exec source.compile() in miniglobals
        self.unpack = miniglobals['unpack'] # override not-rpython version

    def _freeze_(self):
        assert self.formats
        self._create_unpacking_func()
        return True

@specialize.memo()
def create_unpacker(unpack_str):
    fmtiter = FrozenUnpackIterator(unpack_str)
    fmtiter.interpret(unpack_str)
    assert fmtiter._freeze_()
    return fmtiter

@specialize.arg(0)
def runpack(fmt, input):
    unpacker = create_unpacker(fmt)
    return unpacker.unpack(input)
