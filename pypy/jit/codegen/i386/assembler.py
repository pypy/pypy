import struct
from types import StringType
from cStringIO import StringIO

from i386 import *


def constant32(value):
    if -128 <= value < 128:
        return IMM8, value
    else:
        return IMM32, value


class jumpmarker:
    def __init__(self, label, instrindex):
        self.label = label
        self.instrindex = instrindex

class quote:
    def __init__(self, source):
        self.source = source
    def __repr__(self):
        return 'quote(%r)' % (self.source,)


class CodeBuilder:
    
    def __init__(self):
        self.buffer = StringIO()
        self.reloc = []
        
    def write(self, data):
        self.buffer.write(data)

    def position(self):
        return self.buffer.tell()

    def correct(self, position, width, value):
        self.buffer.seek(position)
        self.buffer.write(struct.pack(width, value))

    def writeimmediate(self, immed, width='i', relative=None):
        if relative is not None:
            assert width == 'i' and relative == 4
            self.reloc.append(self.position())
        elif isinstance(immed, jumpmarker):
            immed.position = self.position()
            immed.width = width
            immed = 0
        if immed >= 0:
            width = width.upper()
        self.buffer.write(struct.pack(width, immed))

##    def codeobject(self):
##        import psyco
##        cs = psyco.copybuffer(self.buffer.getvalue())
##        addr = psyco.addressof(cs)
##        for p in self.reloc:
##            abstarget, = struct.unpack('i', cs[p:p+4])
##            cs[p:p+4] = struct.pack('I', sub32(abstarget, addr+p+4))
##        return cs

    def dumpcodeobject(self):
        return "".join(["%02X " % ord(x) for x in self.buffer.getvalue()]),  \
               self.reloc


class HigherBuilder(CodeBuilder):

    def __init__(self):
        CodeBuilder.__init__(self)
        self.result = []
        self.targacc = 0

    def writeimmediate(self, immed, width='i', relative=None):
        if relative is not None:
            assert width == 'i' and relative == 4
            self.flushtargacc()
            self.result.append('<relocation to %s>' % immed)
        elif isinstance(immed, jumpmarker):
            self.result.append('<jump target>')
        if isinstance(immed, quote):
            assert width == 'i'
            self.result_strings()
            self.result.append((MOV,
                                (MODRM, (memBase, (EDI, self.targacc))),
                                immed.source))
            self.targacc += 4
        else:
            CodeBuilder.writeimmediate(self, immed, width, relative)

    def result_strings(self):
        basecode = self.buffer.getvalue()
        self.buffer.seek(0)
        self.buffer.truncate()
        extra = (len(basecode) & 3 == 3)   # 0 or 1
        basecode += '\000' * extra
        while len(basecode) >= 4:
            value, = struct.unpack('i', basecode[:4])
            self.result.append((MOV,
                                (MODRM, (memBase, (EDI, self.targacc))),
                                constant32(value)))
            self.targacc += 4
            basecode = basecode[4:]
        for c in basecode:
            value, = struct.unpack('b', c)
            self.result.append((MOV,
                                (MODRM8, (memBase, (EDI, self.targacc))),
                                (IMM8,   value)))
            self.targacc += 1
        self.targacc -= extra

    def flushtargacc(self, sub_from_edi=0):
        tacc = sub32(self.targacc + self.buffer.tell(), sub_from_edi)
        if tacc:
            self.result.append((ADD,  (EDI, None),  constant32(tacc)))
            self.targacc = sub32(sub_from_edi, self.buffer.tell())

    def dumpcodeobject(self, sub_from_edi=0):
        self.result_strings()
        self.flushtargacc(sub_from_edi)
        return self.result


def Encode(instrs, coder=CodeBuilder):
    farjumps = {}
    while 1:
        valid = 1
        labels = {}
        jumpmarkers = []
        s = coder()
        for j, instr in zip(range(len(instrs)), instrs):
            if type(instr) is StringType:
                assert not labels.has_key(instr)  # label already defined
                labels[instr] = s.position()
            else:
                i = instr[0]
                args = instr[1:]
                if i.indirect and args and type(args[-1]) is StringType:
                    m = farjumps.get(j, REL8)
                    jm = jumpmarker(args[-1],j)
                    jumpmarkers.append(jm)
                    args = args[:-1] + ((m, jm),)
                i.encode(s, *args)
        for marker in jumpmarkers:
            size = struct.calcsize(marker.width)
            origin = marker.position + size
            offset = labels[marker.label] - origin  # KeyError: label not found
            if size == 1 and not single_byte(offset):
                valid = 0
                farjumps[marker.instrindex] = REL32
            elif valid:
                s.correct(marker.position, marker.width, offset)
        if valid:
            return s.dumpcodeobject()

#etest = Encode([(MOV, (EAX,None), (IMM32, quote((EAX,None))))],
#                      HigherBuilder)
##etest = Encode(etest, HigherBuilder)
#for e in etest:
#    print e
#print Encode(etest)
