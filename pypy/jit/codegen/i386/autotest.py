import os, random, string, struct
import i386

FILENAME = 'checkfile.tmp'
BEGIN_TAG = '<<<ri386-test-begin>>>'
END_TAG =   '<<<ri386-test-end>>>'

COUNT1 = 15
COUNT2 = 25


def modrm((memoryfn, args)):
    if memoryfn == i386.memRegister:
        register, = args
        return opnames[register]()
    if memoryfn == i386.memBase:
        base, offset = args
        index = scale = None
    elif memoryfn == i386.memSIB:
        base, index, scale, offset = args
    else:
        raise "???"
    if offset:
        s = "%d" % offset
    else:
        s = ""
    if index is None:
        if base is not None:
            s += "(%s)" % opnames[base]()
    else:
        if base is None:
            sbase = ""
        else:
            sbase = opnames[base]()
        s += "(%s,%s,%d)" % (sbase, opnames[index](), 1<<scale)
    return s or "0"

opnames = {
    i386.EAX: "%eax",
    i386.ECX: "%ecx",
    i386.EDX: "%edx",
    i386.EBX: "%ebx",
    i386.ESP: "%esp",
    i386.EBP: "%ebp",
    i386.ESI: "%esi",
    i386.EDI: "%edi",

    i386.AL: "%al",
    i386.CL: "%cl",
    i386.DL: "%dl",
    i386.BL: "%bl",
    i386.AH: "%ah",
    i386.CH: "%ch",
    i386.DH: "%dh",
    i386.BH: "%bh",

    i386.REG: lambda reg: opnames[reg],
    i386.MODRM: modrm,
    i386.IMM32: lambda x: '$%d' % x,
    i386.REG8: lambda reg: openames[reg],
    i386.MODRM8: modrm,
    i386.IMM8: lambda x: '$%d' % x,
    i386.IMM16: lambda x: '$%d' % x,
    
    "%d": lambda x: '%d' % x,
    i386.REL8: lambda x: "L%d%+d" % (labelcount, x),
    i386.REL32: lambda x: "L%d%+d" % (labelcount, x),
    }

sizes = {
    i386.EAX: 4,
    i386.ECX: 4,
    i386.EDX: 4,
    i386.EBX: 4,
    i386.ESP: 4,
    i386.EBP: 4,
    i386.ESI: 4,
    i386.EDI: 4,

    i386.AL: 1,
    i386.CL: 1,
    i386.DL: 1,
    i386.BL: 1,
    i386.AH: 1,
    i386.CH: 1,
    i386.DH: 1,
    i386.BH: 1,

    i386.REG: 4,
    i386.MODRM: 4,
    i386.IMM32: 4,
    i386.REG8: 1,
    i386.MODRM8: 1,
    i386.IMM8: 1,
    i386.IMM16: 2,
    i386.REL8: 1,
    i386.REL32: 4,
}

suffixes = {0:'', 1:'b', 2:'w', 4:'l'}

def single_test():
    return [None]

def no_tests():
    return []

def imm8_tests():
    return [-128,-1,0,1,127] + [random.randrange(-127, 127) for i in range(COUNT1)]

def imm16_tests():
    return [-32768,32767] + [random.randrange(-32767, -128) for i in range(COUNT1)] \
           + [random.randrange(128, 32767) for i in range(COUNT1)]

def imm32_tests():
    v = [0x80000000,0x7FFFFFFF] + [random.randrange(0,65536)<<16 | random.randrange(0,65536) for i in range(COUNT1)]
    return filter(lambda x: x<-128 or x>=128, v)

def pick1(cache=[]):
    base = random.randrange(-3,8)
    if base<0: base=None
    index = random.randrange(-3,8)
    if index<0 or index==i386.ESP: index=None
    scale = random.randrange(0,4)
    if not cache:
        cache[:] = imm8_tests() + imm32_tests() + [0,0]
        random.shuffle(cache)
    offset = cache.pop()
    if base is None and scale==0:
        base = index
        index = None
    return (i386.memSIB, (base, index, scale, offset))

def modrm_tests():
    return [pick1() for i in range(COUNT2)] #+ [(i386.memRegister, (r,)) for r in range(8)]

def modrm8_tests():
    return [pick1() for i in range(COUNT2)] #+ [(i386.memRegister, (r,)) for r in range(8,16)]

tests = {
    i386.REG: no_tests,
    i386.MODRM: modrm_tests,
    i386.IMM32: imm32_tests,
    i386.REG8: no_tests,
    i386.MODRM8: modrm8_tests,
    i386.IMM8: imm8_tests,
    i386.IMM16: imm16_tests,
    i386.REL8: imm8_tests,
    i386.REL32: imm32_tests,
    }

def setup():
    for key, value in opnames.items():
        if type(value) is type(""):
            opnames[key] = lambda dummy=None, result=value: result
            tests[key] = single_test
setup()

def test(instrs):
    global labelcount
    labelcount = 0
    oplist = []
    g = os.popen('as -o %s' % FILENAME, 'w')
    g.write('\x09.string "%s"\n' % BEGIN_TAG)
    for instrname, args in instrs:
        suffix = ""
        instr = getattr(i386, instrname)
        instrname = instr.as_alias or instrname
        all = instr.as_all_suffixes
        for m, extra in args:
            if m in (i386.MODRM, i386.MODRM8) or all:
                suffix = suffixes[sizes[m]] + suffix
        following = ""
        if instr.indirect:
            suffix = ""
            if args[-1][0] in (i386.REL8,i386.REL32):
                labelcount += 1
                following = "\nL%d:" % labelcount
            elif args[-1][0] in (i386.IMM8,i386.IMM32):
                args = list(args)
                args[-1] = ("%d", args[-1][1])  # no '$' sign
            else:
                suffix += " *"
            k = -1
        else:
            k = len(args)
        for m, extra in args[:k]:
            assert m not in (i386.REL8,i386.REL32)
        ops = [opnames[m](extra) for m, extra in args]
        ops.reverse()
        op = '\x09%s%s %s%s' % (instrname, suffix, string.join(ops, ", "),
                                following)
        g.write('%s\n' % op)
        oplist.append(op)
    g.write('\x09.string "%s"\n' % END_TAG)
    g.close()
    try:
        f = open(FILENAME, 'rb')
    except IOError:
        for op in oplist:
            print op
        raise "Assembler error"
    data = f.read()
    f.close()
    os.unlink(FILENAME)
    i = string.find(data, BEGIN_TAG)
    assert i>=0
    j = string.find(data, END_TAG, i)
    assert j>=0
    as_code = data[i+len(BEGIN_TAG)+1:j]
    return oplist, as_code

##def getreg(m, extra):
##    if m>=0:
##        return m
##    if m==i386.REG or m==i386.REG8:
##        return extra
##    if m==i386.MODRM or m==i386.MODRM8:
##        if extra[0]==i386.memRegister:
##            return extra[1][0]

def test_all_rec(instrname, modes, args=[]):
    if modes:
        m = modes[0]
        lst = tests[m]()
        random.shuffle(lst)
        result = []
        for extra in lst:
            result += test_all_rec(instrname, modes[1:], args+[(m,extra)])
        return result
    else:
        if instrname == "MOV":
            #m0, extra0 = args[0]
            #m1, extra1 = args[1]
            #if m0 in (i386.REG,i386.REG8) or m0>=0 \
            #   and m1 in (i386.MODRM,i386.MODRM8) \
            #   and extra1[0]==i386.memRegister:
            #    return
            #r0 = getreg(m0, extra0)
            #r1 = getreg(m1, extra1)
            #if code1 == "" and r0 != None and r0 == r1:
            #    return
            if args[0] == args[1]:
                return []   # MOV reg, same reg
            if (args[0][0] in (i386.EAX, i386.AL))  \
               and args[1][0] in (i386.MODRM, i386.MODRM8)  \
               and args[1][1][0] == i386.memSIB  \
               and args[1][1][1][:2] == (None,None):
                return []   # MOV accum, [constant-address]
            if (args[1][0] in (i386.EAX, i386.AL))  \
               and args[0][0] in (i386.MODRM, i386.MODRM8)  \
               and args[0][1][0] == i386.memSIB  \
               and args[0][1][1][:2] == (None,None):
                return []   # MOV [constant-address], accum
        return [(instrname, args)]

def hexdump(s):
    return string.join(["%02X" % ord(c) for c in s], " ")


class CodeChecker:
    
    def __init__(self, expected):
        self.expected = expected
        self.index = 0

    def begin(self, op):
        self.op = op
        self.instrindex = self.index

    def write(self, data):
        end = self.index+len(data)
        if data != self.expected[self.index:end]:
            print self.op
            print "\x09from i386.py:", hexdump(self.expected[self.instrindex:self.index] + data)+"..."
            print "\x09from as:     ", hexdump(self.expected[self.instrindex:end])+"..."
            raise "Differs"
        self.index += len(data)
    
    def writeimmediate(self, immed, width='i', relative=None):
        if relative is not None:
            assert width == 'i'
            immed = i386.sub32(immed, relative)
        if immed >= 0:
            width = width.upper()
        self.write(struct.pack(width, immed))


def complete_test(instrname, instr):
    print "Testing %s\x09(%d encodings)" % (instrname, len(instr.encodings))
    ilist = []
    for modes, code in instr.encodings.items():
        ilist += test_all_rec(instrname, modes)
    oplist, as_code = test(ilist)
    cc = CodeChecker(as_code)
    for op, (instrname, args) in zip(oplist, ilist):
        if op:
            cc.begin(op)
            instr.encode(cc, *tuple(args))

def complete_tests():
    FORBIDDEN = ['CMOVPE', 'CMOVPO']    # why doesn't 'as' know about them?
    items = i386.__dict__.items()
    items.sort()
    for key, value in items:
        if isinstance(value, i386.Instruction):
            if key in FORBIDDEN:
                print "Skipped", key
            else:
                complete_test(key,value)
    print "Ok."

if __name__ == "__main__":
    #complete_test("TEST", i386.TEST)
    complete_tests()
