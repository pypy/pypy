LOC_REG       = 0
LOC_ESP_PLUS  = 1
LOC_EBP_PLUS  = 2
LOC_EBP_MINUS = 3
LOC_MASK      = 0x03
LOC_NOWHERE   = LOC_REG | 0

# x86-32 registers sometimes used to pass arguments when gcc optimizes
# a function's calling convention
ARGUMENT_REGISTERS_32 = ('%eax', '%edx', '%ecx')

# x86-64 registers used to pass arguments
ARGUMENT_REGISTERS_64 = ('%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9')


def frameloc_esp(offset):
    assert offset >= 0
    assert offset % 4 == 0
    return LOC_ESP_PLUS | offset

def frameloc_ebp(offset):
    assert offset % 4 == 0
    if offset >= 0:
        return LOC_EBP_PLUS | offset
    else:
        return LOC_EBP_MINUS | (-offset)


class SomeNewValue(object):
    def __repr__(self):
        return 'somenewvalue'
somenewvalue = SomeNewValue()

class LocalVar(object):
    # A local variable location at position 'ofs_from_frame_end',
    # which is counted from the end of the stack frame (so it is always
    # negative, unless it refers to arguments of the current function).
    def __init__(self, ofs_from_frame_end, hint=None):
        self.ofs_from_frame_end = ofs_from_frame_end
        self.hint = hint

    def __repr__(self):
        return '<%+d;%s>' % (self.ofs_from_frame_end, self.hint or 'e*p')

    def __hash__(self):
        return hash(self.ofs_from_frame_end)

    def __cmp__(self, other):
        if isinstance(other, LocalVar):
            return cmp(self.ofs_from_frame_end, other.ofs_from_frame_end)
        else:
            return 1

    def getlocation(self, framesize, uses_frame_pointer, wordsize):
        if (self.hint == 'esp' or not uses_frame_pointer
            or self.ofs_from_frame_end % 2 != 0):
            # try to use esp-relative addressing
            ofs_from_esp = framesize + self.ofs_from_frame_end
            if ofs_from_esp % 2 == 0:
                return frameloc_esp(ofs_from_esp)
            # we can get an odd value if the framesize is marked as bogus
            # by visit_andl()
        assert uses_frame_pointer
        ofs_from_ebp = self.ofs_from_frame_end + wordsize
        return frameloc_ebp(ofs_from_ebp)


class Insn(object):
    _args_ = []
    _locals_ = []
    hack = None

    def __repr__(self):
        return '%s(%s) --- %r' % (self.__class__.__name__,
                           ', '.join([str(getattr(self, name))
                                      for name in self._args_]),
                                  self.hack)
    def requestgcroots(self, tracker):
        return {}

    def source_of(self, localvar, tag):
        if tag is None:
            if self.hack is None:
                self.hack = set()
            self.hack.add(localvar)
        return localvar

    def all_sources_of(self, localvar):
        return [localvar]

class InsnCondJump(Insn):     # only for debugging; not used internally
    _args_ = ['label']
    def __init__(self, label):
        self.label = label

class Label(Insn):
    _args_ = ['label', 'lineno']
    def __init__(self, label, lineno):
        self.label = label
        self.lineno = lineno
        self.previous_insns = []   # all insns that jump (or fallthrough) here

class InsnFunctionStart(Insn):
    _args_ = ['arguments']
    framesize = 0
    previous_insns = ()
    def __init__(self, registers, wordsize):
        self.arguments = {}
        for reg in registers:
            self.arguments[reg] = somenewvalue
        self.wordsize = wordsize

    def source_of(self, localvar, tag):
        if localvar not in self.arguments:
            if self.wordsize == 4 and localvar in ARGUMENT_REGISTERS_32:
                # xxx this might show a bug in trackgcroot.py failing to
                # figure out which instruction stored a value in these
                # registers.  However, this case also occurs when the
                # the function's calling convention was optimized by gcc:
                # the 3 registers above are then used to pass arguments
                pass
            elif self.wordsize == 8 and localvar in ARGUMENT_REGISTERS_64:
                # this is normal: these registers are always used to
                # pass arguments
                pass
            else:
                assert (isinstance(localvar, LocalVar) and
                        localvar.ofs_from_frame_end > 0), (
                    "must come from an argument to the function, got %r" %
                    (localvar,))
            self.arguments[localvar] = somenewvalue
        return self.arguments[localvar]

    def all_sources_of(self, localvar):
        return []

class InsnSetLocal(Insn):
    _args_ = ['target', 'sources']
    _locals_ = ['target', 'sources']

    def __init__(self, target, sources=()):
        self.target = target
        self.sources = sources

    def source_of(self, localvar, tag):
        if localvar == self.target:
            return somenewvalue
        return Insn.source_of(self, localvar, tag)

    def all_sources_of(self, localvar):
        if localvar == self.target:
            return self.sources
        return [localvar]

class InsnCopyLocal(Insn):
    _args_ = ['source', 'target']
    _locals_ = ['source', 'target']

    def __init__(self, source, target):
        self.source = source
        self.target = target

    def source_of(self, localvar, tag):
        if localvar == self.target:
            return self.source
        return Insn.source_of(self, localvar, tag)

    def all_sources_of(self, localvar):
        if localvar == self.target:
            return [self.source]
        return [localvar]

class InsnStackAdjust(Insn):
    _args_ = ['delta']
    def __init__(self, delta):
        assert delta % 2 == 0     # should be "% 4", but there is the special
        self.delta = delta        # case of 'pushw' to handle

class InsnCannotFollowEsp(InsnStackAdjust):
    def __init__(self):
        self.delta = -7     # use an odd value as marker

class InsnStop(Insn):
    _args_ = ['reason']
    def __init__(self, reason='?'):
        self.reason = reason

class InsnRet(InsnStop):
    _args_ = []
    framesize = 0
    def __init__(self, registers):
        self.registers = registers

    def requestgcroots(self, tracker):
        # no need to track the value of these registers in the caller
        # function if we are flagged as a "bottom" function (a callback
        # from C code, or pypy_main_function())
        if tracker.is_stack_bottom:
            return {}
        else:
            return dict(zip(self.registers, self.registers))

class InsnCall(Insn):
    _args_ = ['lineno', 'name', 'gcroots']
    def __init__(self, name, lineno):
        # 'gcroots' is a dict built by side-effect during the call to
        # FunctionGcRootTracker.trackgcroots().  Its meaning is as
        # follows: the keys are the locations that contain gc roots
        # (register names or LocalVar instances).  The value
        # corresponding to a key is the "tag", which is None for a
        # normal gc root, or else the name of a callee-saved register.
        # In the latter case it means that this is only a gc root if the
        # corresponding register in the caller was really containing a
        # gc pointer.  A typical example:
        #
        #   InsnCall({LocalVar(-8)': None,
        #             '%esi': '%esi',
        #             LocalVar(-12)': '%ebx'})
        #
        # means that the value at -8 from the frame end is a gc root
        # across this call; that %esi is a gc root if it was in the
        # caller (typically because %esi is not modified at all in the
        # current function); and that the value at -12 from the frame
        # end is a gc root if %ebx was a gc root in the caller
        # (typically because the current function saves and restores
        # %ebx from there in the prologue and epilogue).
        self.gcroots = {}
        self.lineno = lineno
        self.name = name

    def source_of(self, localvar, tag):
        tag1 = self.gcroots.setdefault(localvar, tag)
        assert tag1 == tag, (
            "conflicting entries for\n%s.gcroots[%s]:\n%r and %r" % (
            self, localvar, tag1, tag))
        return localvar

    def all_sources_of(self, localvar):
        return [localvar]

class InsnGCROOT(Insn):
    _args_ = ['loc']
    _locals_ = ['loc']
    def __init__(self, loc):
        self.loc = loc
    def requestgcroots(self, tracker):
        return {self.loc: None}

class InsnPrologue(Insn):
    def __init__(self, wordsize):
        self.wordsize = wordsize
    def __setattr__(self, attr, value):
        if attr == 'framesize':
            assert value == self.wordsize, (
                "unrecognized function prologue - "
                "only supports push %ebp; movl %esp, %ebp")
        Insn.__setattr__(self, attr, value)

class InsnEpilogue(Insn):
    def __init__(self, framesize=None):
        if framesize is not None:
            self.framesize = framesize
