LOC_NOWHERE   = 0
LOC_REG       = 1
LOC_EBP_BASED = 2
LOC_ESP_BASED = 3
LOC_MASK      = 0x03

def frameloc(base, offset):
    assert base in (LOC_EBP_BASED, LOC_ESP_BASED)
    assert offset % 4 == 0
    return base | offset


class SomeNewValue(object):
    pass
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

    def getlocation(self, framesize, uses_frame_pointer):
        if (self.hint == 'esp' or not uses_frame_pointer
            or self.ofs_from_frame_end % 2 != 0):
            # try to use esp-relative addressing
            ofs_from_esp = framesize + self.ofs_from_frame_end
            if ofs_from_esp % 2 == 0:
                return frameloc(LOC_ESP_BASED, ofs_from_esp)
            # we can get an odd value if the framesize is marked as bogus
            # by visit_andl()
        assert uses_frame_pointer
        ofs_from_ebp = self.ofs_from_frame_end + 4
        return frameloc(LOC_EBP_BASED, ofs_from_ebp)


class Insn(object):
    _args_ = []
    _locals_ = []

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                           ', '.join([str(getattr(self, name))
                                      for name in self._args_]))
    def requestgcroots(self, tracker):
        return {}

    def source_of(self, localvar, tag):
        return localvar

    def all_sources_of(self, localvar):
        return [localvar]

class Label(Insn):
    _args_ = ['label', 'lineno']
    def __init__(self, label, lineno):
        self.label = label
        self.lineno = lineno
        self.previous_insns = []   # all insns that jump (or fallthrough) here

class InsnFunctionStart(Insn):
    framesize = 0
    previous_insns = ()
    def __init__(self, registers):
        self.arguments = {}
        for reg in registers:
            self.arguments[reg] = somenewvalue

    def source_of(self, localvar, tag):
        if localvar not in self.arguments:
            if localvar in ('%eax', '%edx', '%ecx'):
                # xxx this might show a bug in trackgcroot.py failing to
                # figure out which instruction stored a value in these
                # registers.  However, this case also occurs when the
                # the function's calling convention was optimized by gcc:
                # the 3 registers above are then used to pass arguments
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
        return localvar

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
        return localvar

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
    pass

class InsnRet(InsnStop):
    framesize = 0
    def __init__(self, registers):
        self.registers = registers

    def requestgcroots(self, tracker):
        # no need to track the value of these registers in the caller
        # function if we are the main(), or if we are flagged as a
        # "bottom" function (a callback from C code)
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
    def __setattr__(self, attr, value):
        if attr == 'framesize':
            assert value == 4, ("unrecognized function prologue - "
                                "only supports push %ebp; movl %esp, %ebp")
        Insn.__setattr__(self, attr, value)

class InsnEpilogue(Insn):
    def __init__(self, framesize=None):
        if framesize is not None:
            self.framesize = framesize


