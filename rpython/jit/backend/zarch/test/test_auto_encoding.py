import os, random, struct
import subprocess
import py
from rpython.jit.backend.zarch import codebuilder
from rpython.rlib.rarithmetic import intmask
from rpython.tool.udir import udir
import itertools
import re

INPUTNAME = 'checkfile_%s.s'
FILENAME = 'checkfile_%s.o'
BEGIN_TAG = '<<<zarch-test-begin>>>'
END_TAG =   '<<<zarch-test-end>>>'

class CodeCheckerMixin(object):
    def __init__(self, expected, accept_unnecessary_prefix):
        self.expected = expected
        self.accept_unnecessary_prefix = accept_unnecessary_prefix
        self.index = 0

    def begin(self, op):
        self.op = op
        self.instrindex = self.index

    def writechar(self, char):
        if char != self.expected[self.index:self.index+1]:
            if (char == self.accept_unnecessary_prefix
                and self.index == self.instrindex):
                return    # ignore the extra character '\x40'
            print self.op
            post = self.expected[self.index+1:self.index+1+15]
            generated = "\x09from codebuilder.py: " + hexdump(self.expected[self.instrindex:self.index] + char )+"..."
            print generated
            expected = "\x09from         gnu as: " + hexdump(self.expected[self.instrindex:self.index+15])+"..."
            print expected
            raise Exception("Differs:\n" + generated + "\n" + expected)
        self.index += 1

    def done(self):
        assert len(self.expected) == self.index

    def stack_frame_size_delta(self, delta):
        pass   # ignored

    def check_stack_size_at_ret(self):
        pass   # ignored

class CodeCheckerZARCH(CodeCheckerMixin, codebuilder.InstrBuilder):
    pass

def hexdump(s):
    return ' '.join(["%02X" % ord(c) for c in s])

def reduce_to_32bit(s):
    if s[:2] != '%r':
        return s
    if s[2:].isdigit():
        return s + 'd'
    else:
        return '%e' + s[2:]

# ____________________________________________________________

COUNT1 = 15
suffixes = {0:'', 1:'b', 2:'w', 4:'l', 8:'q'}

class FakeIndexBaseDisplace(object):
    def __init__(self, index, base, disp):
        self.index = index
        self.base = base
        self.displace = disp

    def __str__(self):
        disp = self.displace
        index = self.index
        base = self.base
        return "{disp}(%r{index},%r{base})".format(**locals())

class FakeBaseDisplace(object):
    def __init__(self, base, disp):
        self.base = base
        self.displace = disp

    def __str__(self):
        disp = self.displace
        base = self.base
        return "{disp}(%r{base})".format(**locals())

class FakeLengthBaseDisplace(object):
    def __init__(self, len, base, disp):
        self.length = len
        self.base = base
        self.displace = disp

    def __str__(self):
        disp = self.displace
        base = self.base
        length = self.length + 1
        return "{disp}({length},%r{base})".format(**locals())

def build_base_disp(base_bits, displace_bits):
    possibilities = itertools.product(range(base_bits), range(displace_bits))
    results = []
    for (base,disp) in possibilities:
        results.append(FakeBaseDisplace(base,disp))
    return results

def build_idx_base_disp(index_bits, base_bits, displace_bits):
    possibilities = itertools.product(range(index_bits), range(base_bits),
                                      range(displace_bits))
    results = []
    for (index,base,disp) in possibilities:
        results.append(FakeIndexBaseDisplace(index,base,disp))
    return results

def build_len_base_disp(len_bits, base_bits, displace_bits):
    possibilities = itertools.product(range(len_bits), range(base_bits),
                                      range(displace_bits))
    results = []
    for (length,base,disp) in possibilities:
        results.append(FakeLengthBaseDisplace(length,base,disp))
    return results

class TestZARCH(object):
    WORD = 8
    TESTDIR = 'zarch'
    REGS = range(15+1)
    REGNAMES = ['%%r%d' % i for i in REGS]
    accept_unnecessary_prefix = None
    methname = '?'
    BASE_DISPLACE = build_base_disp(8,12)
    BASE_DISPLACE_LONG = build_base_disp(8,20)
    INDEX_BASE_DISPLACE = build_idx_base_disp(8,8,12)
    INDEX_BASE_DISPLACE_LONG = build_idx_base_disp(8,8,20)
    LENGTH4_BASE_DISPLACE = build_len_base_disp(4,8,12)
    LENGTH8_BASE_DISPLACE = build_len_base_disp(8,8,12)

    def reg_tests(self):
        return self.REGS

    def stack_bp_tests(self, count=COUNT1):
        return ([0, 4, -4, 124, 128, -128, -132] +
                [random.randrange(-0x20000000, 0x20000000) * 4
                 for i in range(count)])

    def stack_sp_tests(self, count=COUNT1):
        return ([0, 4, 124, 128] +
                [random.randrange(0, 0x20000000) * 4
                 for i in range(count)])

    def memory_tests(self):
        return [(reg, ofs)
                    for reg in self.NONSPECREGS
                    for ofs in self.stack_bp_tests(5)
                ]

    def array_tests(self):
        return [(reg1, reg2, scaleshift, ofs)
                    for reg1 in self.NONSPECREGS
                    for reg2 in self.NONSPECREGS
                    for scaleshift in [0, 1, 2, 3]
                    for ofs in self.stack_bp_tests(1)
                ]

    def imm_tests(self, name, modes, index):
        from rpython.jit.backend.zarch.codebuilder import AbstractZARCHBuilder
        import inspect
        func = getattr(AbstractZARCHBuilder, name)
        args = inspect.getargspec(func).args
        # 1 off, self is first arg
        match = re.compile("(u?imm\d+)").match(args[index+1])
        assert match
        return getattr(self, match.group(1) + "_tests")()

    def uimm16_tests(self):
        v = ([0,1,65535] +
             [random.randrange(0,65535) for i in range(COUNT1)])
        return v
    def imm16_tests(self):
        v = ([-32768,-1,0,1,32767] +
             [random.randrange(-32768, 32767) for i in range(COUNT1)])
        return v

    def imm8_tests(self):
        v = ([-128,-1,0,1,127] +
             [random.randrange(-127, 127) for i in range(COUNT1)])
        return v
    def uimm8_tests(self):
        v = ([0,1,255] +
             [random.randrange(0,255) for i in range(COUNT1)])
        return v
    def uimm4_tests(self):
        return list(range(0,16))

    def imm32_tests(self):
        v = ([-0x80000000, 0x7FFFFFFF, 128, 256, -129, -255] +
             [random.randrange(-32768,32768)<<16 |
                 random.randrange(0,65536) for i in range(COUNT1)] +
             [random.randrange(128, 256) for i in range(COUNT1)])
        return self.imm8_tests() + v

    def relative_tests(self):
        py.test.skip("explicit test required for %r" % (self.methname,))

    def assembler_operand_reg(self, regnum):
        return self.REGNAMES[regnum]

    def get_mapping_asm_to_str(self):
        return {
            'r': self.assembler_operand_reg,
            's': lambda x: str(x),
            'x': lambda x: str(x),
            'y': lambda x: str(x),
            'i': lambda x: str(x),
            'l': lambda x: str(x),
            'L': lambda x: str(x),
        }

    def operand_combinations(self, modes, arguments):
        remap = {
            'rxy': 'rx',
            'siy': 'si',
            'rre': 'rr',
            'ssa': 'Ls',
            'ssb': 'll',
            'ssc': 'lsi',
            'ssd': 'xsr',
            'sse': 'rrss',
        }
        mapping = self.get_mapping_asm_to_str()
        modes = remap.get(modes, modes)
        for mode, args in zip(modes, arguments):
            yield mapping[mode](args)

    def run_test(self, methname, instrname, argmodes, args_lists,
                 instr_suffix=None):
        global labelcount
        labelcount = 0
        oplist = []
        testdir = udir.ensure(self.TESTDIR, dir=1)
        inputname = str(testdir.join(INPUTNAME % methname))
        filename  = str(testdir.join(FILENAME  % methname))
        with open(inputname, 'w') as g:
            g.write('\x09.string "%s"\n' % BEGIN_TAG)
            #
            for args in args_lists:
                suffix = ""
                if instr_suffix is not None:
                    suffix = instr_suffix    # overwrite
                #
                ops = self.operand_combinations(argmodes, args)
                op = '\t%s%s %s' % (instrname.lower(), suffix,
                                      ', '.join(ops))
                g.write('%s\n' % op)
                oplist.append(op)
            g.write('\t.string "%s"\n' % END_TAG)
        proc = subprocess.Popen(['as', '-m' + str(self.WORD*8), '-mzarch',
                                 inputname, '-o', filename],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        if proc.returncode or stderr:
            raise Exception("could not execute assembler. error:\n%s" % (stderr))
        with open(inputname, 'r') as g:
            got = g.read()
        error = [line for line in got.splitlines() if 'error' in line.lower()]
        if error:
            raise Exception("Assembler got an error: %r" % error[0])
        error = [line for line in got.splitlines()
                 if 'warning' in line.lower()]
        if error:
            raise Exception("Assembler got a warning: %r" % error[0])
        try:
            with open(filename, 'rb') as f:
                data = f.read()
                i = data.find(BEGIN_TAG)
                assert i>=0
                j = data.find(END_TAG, i)
                assert j>=0
                as_code = data[i+len(BEGIN_TAG)+1:j]
        except IOError:
            raise Exception("Assembler did not produce output?")
        return oplist, as_code

    def modes(self, mode):
        return mode

    def make_all_tests(self, methname, modes, args=[]):
        tests = {
            'r': lambda i: self.REGS,
            'x': lambda i: self.INDEX_BASE_DISPLACE,
            'y': lambda i: self.INDEX_BASE_DISPLACE_LONG,
            'i': lambda i: self.imm_tests(methname, modes, i),
            's': lambda i: self.BASE_DISPLACE,
            'L': lambda i: self.LENGTH8_BASE_DISPLACE,
            'l': lambda i: self.LENGTH4_BASE_DISPLACE,
        }
        tests_all = {
            'rxy': (tests['r'], tests['y']),
            'siy': (lambda i: self.BASE_DISPLACE_LONG, tests['i']),
            'rre': (tests['r'], tests['r']),
            'ssa': (tests['L'], tests['s']),
            'ssb': (tests['l'], tests['l']),
            'ssc': (tests['l'], tests['s'], tests['i']),
        }
        if modes in tests_all:
            combinations = [f(i) for i,f in enumerate(tests_all[modes])]
        else:
            combinations = []
            for i,m in enumerate(modes):
                elems = tests[m](i)
                random.shuffle(elems)
                combinations.append(elems)
        results = []
        for args in itertools.product(*combinations):
            results.append(args)
        return results

    def should_skip_instruction(self, instrname, argmodes):
        return False

    def complete_test(self, methname):
        if '_' in methname:
            instrname, argmodes = methname.split('_')
        else:
            instrname, argmodes = methname, ''
        argmodes = self.modes(argmodes)

        if self.should_skip_instruction(instrname, argmodes):
            print "Skipping %s" % methname
            return

        instr_suffix = None

        print "Testing %s with argmodes=%r" % (instrname, argmodes)
        self.methname = methname
        ilist = self.make_all_tests(methname, argmodes)
        oplist, as_code = self.run_test(methname, instrname, argmodes, ilist,
                                        instr_suffix)
        cc = CodeCheckerZARCH(as_code, self.accept_unnecessary_prefix)
        for op, args in zip(oplist, ilist):
            if op:
                cc.begin(op)
                getattr(cc, methname)(*args)
        cc.done()

    def setup_class(cls):
        import os
        g = os.popen('as -version </dev/null -o /dev/null 2>&1')
        data = g.read()
        g.close()
        if not data.startswith('GNU assembler'):
            py.test.skip("full tests require the GNU 'as' assembler")

    @py.test.mark.parametrize("name", codebuilder.all_instructions)
    def test_all(self, name):
        self.complete_test(name)
