from pypy.jit.metainterp import codewriter
import sys

class SourceIterator:

    def __init__(self, jitcode, source, interpreter, labelpos):
        self.jitcode = jitcode
        self.source = source
        self.interpreter = interpreter
        self.labelpos = labelpos
        self.index = 0
        self.pc = 0

    def finished(self):
        return self.index == len(self.source)

    def peek(self):
        return self.source[self.index]

    def get(self, expected_type, bytes_count):
        arg = self.source[self.index]
        assert isinstance(arg, expected_type)
        self.index += 1
        self.pc += bytes_count
        return arg

    def get_opname(self):
        return self.get(str, 1)

    def getjitcode(self):
        return self.jitcode

    def load_int(self):
        result = self.get(int, 0)
        self.pc += len(codewriter.encode_int(result))
        return result

    def load_bool(self):
        return self.get(bool, 1)

    def load_arg(self):
        return self.getenv(self.load_int())

    def load_const_arg(self):
        return self.jitcode.constants[self.load_int()]

    def getenv(self, i):
        if i % 2:
            return self.jitcode.constants[i // 2]
        return CustomRepr('r%d' % (i // 2))

    def load_varargs(self):
        count = self.load_int()
        return [self.load_arg() for i in range(count)]

    def load_constargs(self):
        count = self.load_int()
        return [self.load_const_arg() for i in range(count)]

    def get_redarg(self):
        return CustomRepr('r%d' % self.load_int())

    def get_greenkey(self):
        keydescnum = self.load_int()
        if keydescnum == 0:
            return None
        else:
            keydesc = self.jitcode.keydescs[keydescnum - 1]
            return keydesc

    def load_3byte(self):     # for jump targets
        tlbl = self.get(codewriter.tlabel, 3)
        return 'pc: %d' % self.labelpos[tlbl.name]

    def make_result_box(self, box):
        pass


class CustomRepr:
    def __init__(self, s):
        self.s = s
    def __repr__(self):
        return self.s

def dump_bytecode(jitcode, file=None):
    # XXX this is not really a disassembler, but just a pretty-printer
    # for the '_source' attribute that codewriter.py attaches
    source = jitcode._source
    interpreter = jitcode._metainterp_sd
    labelpos = jitcode._labelpos
    print >> file, 'JITCODE %r' % (jitcode.name,)
    if interpreter.opcode_implementations is None:
        return     # for tests

    src = SourceIterator(jitcode, source, interpreter, labelpos)
    noblankline = {0: True}
    while not src.finished():
        arg = src.peek()
        if isinstance(arg, str):
            startpc = src.pc
            opname = src.get_opname()
            opcode = interpreter.find_opcode(opname)
            opimpl = interpreter.opcode_implementations[opcode]

            args = []
            def wrapper_callback(src, *newargs):
                args.extend(newargs)
            opimpl.argspec(wrapper_callback)(src, 'pc')

            args = map(str, args)

            comments = []
            while (not src.finished() and isinstance(src.peek(), str)
                   and src.peek().startswith('#')):
                # comment, used to tell where the result of the previous
                # operation goes
                comments.append(src.get(str, 0)[1:].strip())

            if startpc == 0:
                startpc = 'pc: 0'
            line = '%5s |  %-20s %-16s %s' % (startpc, opname,
                                              ', '.join(args),
                                              ', '.join(comments))
            print >> file, line.rstrip()
        elif isinstance(arg, codewriter.label):
            if src.pc not in noblankline:    # no duplicate blank lines
                print >> file, '%5s |' % ''
                noblankline[src.pc] = True
            src.index += 1
        else:
            assert 0, "unexpected object: %r" % (arg,)

    if src.pc != len(jitcode.code):
        print >> file, 'WARNING: the pc column is bogus! fix dump.py!'
