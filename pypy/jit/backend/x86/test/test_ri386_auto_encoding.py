import os, random, string, struct
import py
from pypy.jit.backend.x86 import ri386 as i386
from pypy.jit.backend.x86.ri386setup import all_instructions
from pypy.tool.udir import udir

INPUTNAME = str(udir.join('checkfile.s'))
FILENAME = str(udir.join('checkfile.tmp'))
BEGIN_TAG = '<<<ri386-test-begin>>>'
END_TAG =   '<<<ri386-test-end>>>'

COUNT1 = 15
COUNT2 = 25


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
    i386.MODRM64: 8,
    i386.IMM32: 4,
    i386.REG8: 1,
    i386.MODRM8: 1,
    i386.IMM8: 1,
    i386.IMM16: 2,
    #i386.REL8: 1,
    i386.REL32: 4,
}

suffixes = {0:'', 1:'b', 2:'w', 4:'l'}

def reg_tests():
    return i386.registers[:]

def reg8_tests():
    return i386.registers8[:]

def imm8_tests():
    v = [-128,-1,0,1,127] + [random.randrange(-127, 127) for i in range(COUNT1)]
    return map(i386.imm8, v)

def imm16_tests():
    v = [-32768,32767] + [random.randrange(-32767, -128) for i in range(COUNT1)] \
           + [random.randrange(128, 32767) for i in range(COUNT1)]
    return map(i386.imm16, v)

def imm32_tests():
    v = ([0x80000000, 0x7FFFFFFF, 128, 256, -129, -255] +
         [random.randrange(0,65536)<<16 |
             random.randrange(0,65536) for i in range(COUNT1)] +
         [random.randrange(128, 256) for i in range(COUNT1)])
    return map(i386.imm32, filter(lambda x: x<-128 or x>=128, v))

def pick1(memSIB, cache=[]):
    base = random.choice([None, None, None] + i386.registers)
    index = random.choice([None, None, None] + i386.registers)
    if index is i386.esp: index=None
    scale = random.randrange(0,4)
    if not cache:
        cache[:] = [x.value for x in imm8_tests() + imm32_tests()] + [0,0]
        random.shuffle(cache)
    offset = cache.pop()
    if base is None and scale==0:
        base = index
        index = None
    return memSIB(base, index, scale, offset)

def modrm_tests():
    return i386.registers + [pick1(i386.memSIB) for i in range(COUNT2)]

def modrm_noreg_tests():
    return [pick1(i386.memSIB) for i in range(COUNT2)]

def modrm64_tests():
    return [pick1(i386.memSIB64) for i in range(COUNT2)]

def xmm_tests():
    return i386.xmm_registers[:]

def modrm8_tests():
    return i386.registers8 + [pick1(i386.memSIB8) for i in range(COUNT2)]

tests = {
    i386.EAX: lambda: [i386.eax],
    i386.ECX: lambda: [i386.ecx],
    i386.EDX: lambda: [i386.edx],
    i386.EBX: lambda: [i386.ebx],
    i386.ESP: lambda: [i386.esp],
    i386.EBP: lambda: [i386.ebp],
    i386.ESI: lambda: [i386.esi],
    i386.EDI: lambda: [i386.edi],

    i386.AL: lambda: [i386.al],
    i386.CL: lambda: [i386.cl],
    i386.DL: lambda: [i386.dl],
    i386.BL: lambda: [i386.bl],
    i386.AH: lambda: [i386.ah],
    i386.CH: lambda: [i386.ch],
    i386.DH: lambda: [i386.dh],
    i386.BH: lambda: [i386.bh],

    i386.REG: reg_tests,
    i386.MODRM: modrm_tests,
    i386.MODRM64: modrm64_tests,
    i386.XMMREG: xmm_tests,
    i386.IMM32: imm32_tests,
    i386.REG8: reg8_tests,
    i386.MODRM8: modrm8_tests,
    i386.IMM8: imm8_tests,
    i386.IMM16: imm16_tests,
    #i386.REL8: imm8_tests,
    i386.REL32: lambda: [], # XXX imm32_tests,
    }

def run_test(instrname, instr, args_lists):
    global labelcount
    instrname = instr.as_alias or instrname
    labelcount = 0
    oplist = []
    g = open(INPUTNAME, 'w')
    g.write('\x09.string "%s"\n' % BEGIN_TAG)
    for args in args_lists:
        suffix = ""
        all = instr.as_all_suffixes
        for m, extra in args:
            if m in (i386.MODRM, i386.MODRM8) or all:
                if instrname != 'FNSTCW':
                    suffix = suffixes[sizes[m]] + suffix
            if m is i386.MODRM64 and instrname in ['FST', 'FSTP']:
                suffix = 'l'
        following = ""
        if instr.indirect:
            suffix = ""
            if args[-1][0] == i386.REL32: #in (i386.REL8,i386.REL32):
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
            assert m != i386.REL32  #not in (i386.REL8,i386.REL32)
        ops = [extra.assembler() for m, extra in args]
        ops.reverse()
        op = '\x09%s%s %s%s' % (instrname, suffix, string.join(ops, ", "),
                                following)
        g.write('%s\n' % op)
        oplist.append(op)
    g.write('\x09.string "%s"\n' % END_TAG)
    g.close()
    os.system('as "%s" -o "%s"' % (INPUTNAME, FILENAME))
    try:
        f = open(FILENAME, 'rb')
    except IOError:
        raise Exception("Assembler error")
    data = f.read()
    f.close()
##    os.unlink(FILENAME)
##    os.unlink(INPUTNAME)
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

def rec_test_all(instrname, modes, args=[]):
    if modes:
        m = modes[0]
        if instrname.startswith('F') and m is i386.MODRM:
            lst = modrm_noreg_tests()
        else:
            lst = tests[m]()
        random.shuffle(lst)
        result = []
        for extra in lst:
            result += rec_test_all(instrname, modes[1:], args+[(m,extra)])
        return result
    else:
        if instrname == "MOV":
##            if args[0] == args[1]:
##                return []   # MOV reg, same reg
            if ((args[0][1] in (i386.eax, i386.al))
                and args[1][1].assembler().lstrip('-').isdigit()):
                return []   # MOV accum, [constant-address]
            if ((args[1][1] in (i386.eax, i386.al))
                and args[0][1].assembler().lstrip('-').isdigit()):
                return []   # MOV [constant-address], accum
        if instrname == "MOV16":
            return []   # skipped
        if instrname == "CMP16":
            return []   # skipped
        if instrname == "LEA":
            if (args[1][1].__class__ != i386.MODRM or
                args[1][1].is_register()):
                return []
        if instrname == "INT":
            if args[0][1].value == 3:
                return []
        if instrname in ('SHL', 'SHR', 'SAR'):
            if args[1][1].assembler() == '$1':
                return []
        if instrname in ('MOVZX', 'MOVSX'):
            if args[1][1].width == 4:
                return []
        if instrname == "TEST":
            if (args[0] != args[1] and
                isinstance(args[0][1], i386.REG) and
                isinstance(args[1][1], i386.REG)):
                return []   # TEST reg1, reg2  <=>  TEST reg2, reg1
        if instrname.endswith('cond'):
            return []
        return [args]

def hexdump(s):
    return string.join(["%02X" % ord(c) for c in s], " ")


class CodeChecker(i386.I386CodeBuilder):
    
    def __init__(self, expected):
        self.expected = expected
        self.index = 0

    def begin(self, op):
        self.op = op
        self.instrindex = self.index

    def write(self, listofchars):
        data = ''.join(listofchars)
        end = self.index+len(data)
        if data != self.expected[self.index:end]:
            print self.op
            print "\x09from ri386.py:", hexdump(self.expected[self.instrindex:self.index] + data)+"..."
            print "\x09from 'as':    ", hexdump(self.expected[self.instrindex:end])+"..."
            raise Exception("Differs")
        self.index += len(data)


def complete_test(instrname, instr):
    print "Testing %s\x09(%d encodings)" % (instrname, len(instr.modes))
    ilist = []
    for modes in instr.modes:
        ilist += rec_test_all(instrname, modes)
    oplist, as_code = run_test(instrname, instr, ilist)
    cc = CodeChecker(as_code)
    for op, args in zip(oplist, ilist):
        if op:
            cc.begin(op)
            getattr(cc, instrname)(*[extra for m, extra in args])

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

def test_auto():
    import os
    g = os.popen('as -version </dev/null -o /dev/null 2>&1')
    data = g.read()
    g.close()
    if not data.startswith('GNU assembler'):
        py.test.skip("full tests require the GNU 'as' assembler")

    def do_test(name, insn):
        #print name
        if name in ('CMOVPE', 'CMOVPO'):
            py.test.skip("why doesn't 'as' know about CMOVPE/CMOVPO?")
        complete_test(name, insn)

    items = all_instructions.items()
    items.sort()
    for key, value in items:
        yield do_test, key, value
    del key, value

if __name__ == "__main__":
    #complete_test("TEST", i386.TEST)
    complete_tests()
