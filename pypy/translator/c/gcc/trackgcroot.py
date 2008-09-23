#! /usr/bin/env python

import re, sys, os, random

r_functionstart = re.compile(r"\t.type\s+(\w+),\s*[@]function\s*$")
r_functionend   = re.compile(r"\t.size\s+(\w+),\s*[.]-(\w+)\s*$")
r_label         = re.compile(r"([.]?\w+)[:]\s*$")
r_globl         = re.compile(r"\t[.]globl\t(\w+)\s*$")
r_insn          = re.compile(r"\t([a-z]\w*)\s")
r_jump          = re.compile(r"\tj\w+\s+([.]?\w+)\s*$")
OPERAND         =           r"(?:[-\w$%+.:@]+(?:[(][\w%,]+[)])?|[(][\w%,]+[)])"
r_unaryinsn     = re.compile(r"\t[a-z]\w*\s+("+OPERAND+")\s*$")
r_unaryinsn_star= re.compile(r"\t[a-z]\w*\s+([*]"+OPERAND+")\s*$")
r_jmp_switch    = re.compile(r"\tjmp\t[*]([.]?\w+)[(]")
r_jmptable_item = re.compile(r"\t.long\t([.]?\w+)\s*$")
r_jmptable_end  = re.compile(r"\t.text|\t.section\s+.text")
r_binaryinsn    = re.compile(r"\t[a-z]\w*\s+("+OPERAND+"),\s*("+OPERAND+")\s*$")
LOCALVAR        = r"%eax|%edx|%ecx|%ebx|%esi|%edi|%ebp|\d*[(]%esp[)]"
LOCALVARFP      = LOCALVAR + r"|-?\d*[(]%ebp[)]"
r_gcroot_marker = re.compile(r"\t/[*] GCROOT ("+LOCALVARFP+") [*]/")
r_localvarnofp  = re.compile(LOCALVAR)
r_localvarfp    = re.compile(LOCALVARFP)
r_localvar_esp  = re.compile(r"(\d*)[(]%esp[)]")
r_localvar_ebp  = re.compile(r"(-?\d*)[(]%ebp[)]")


class GcRootTracker(object):

    def __init__(self, verbose=0, shuffle=False):
        self.verbose = verbose
        self.shuffle = shuffle     # to debug the sorting logic in asmgcroot.py
        self.clear()

    def clear(self):
        self.gcmaptable = []
        self.seen_main = False
        self.files_seen = 0

    def dump_raw_table(self, output):
        print >> output, "seen_main = %d" % (self.seen_main,)
        for entry in self.gcmaptable:
            print >> output, entry

    def reload_raw_table(self, input):
        firstline = input.readline()
        assert firstline.startswith("seen_main = ")
        self.seen_main |= bool(int(firstline[len("seen_main = "):].strip()))
        for line in input:
            entry = eval(line)
            assert type(entry) is tuple
            self.gcmaptable.append(entry)

    def dump(self, output):
        assert self.seen_main
        shapes = {}
        shapelines = []
        shapeofs = 0
        print >> output, """\t.text
        .globl pypy_asm_stackwalk
            .type pypy_asm_stackwalk, @function
        pypy_asm_stackwalk:
            /* See description in asmgcroot.py */
            movl   4(%esp), %edx     /* my argument, which is the callback */
            movl   %esp, %eax        /* my frame top address */
            pushl  %eax              /* ASM_FRAMEDATA[4] */
            pushl  %ebp              /* ASM_FRAMEDATA[3] */
            pushl  %edi              /* ASM_FRAMEDATA[2] */
            pushl  %esi              /* ASM_FRAMEDATA[1] */
            pushl  %ebx              /* ASM_FRAMEDATA[0] */
            movl   %esp, %eax        /* address of ASM_FRAMEDATA */
            pushl  %eax
            call   *%edx             /* invoke the callback */
            popl   %eax
            popl   %ebx              /* restore from ASM_FRAMEDATA[0] */
            popl   %esi              /* restore from ASM_FRAMEDATA[1] */
            popl   %edi              /* restore from ASM_FRAMEDATA[2] */
            popl   %ebp              /* restore from ASM_FRAMEDATA[3] */
            popl   %eax
            ret
        .size pypy_asm_stackwalk_init, .-pypy_asm_stackwalk_init
        """
        print >> output, '\t.data'
        print >> output, '\t.align\t4'
        print >> output, '\t.globl\t__gcmapstart'
        print >> output, '__gcmapstart:'
        for label, state, is_range in self.gcmaptable:
            try:
                n = shapes[state]
            except KeyError:
                n = shapes[state] = shapeofs
                bytes = [str(b) for b in compress_callshape(state)]
                shapelines.append('\t/*%d*/\t.byte\t%s\n' % (
                    shapeofs,
                    ', '.join(bytes)))
                shapeofs += len(bytes)
            if is_range:
                n = ~ n
            print >> output, '\t.long\t%s' % (label,)
            print >> output, '\t.long\t%d' % (n,)
        print >> output, '\t.globl\t__gcmapend'
        print >> output, '__gcmapend:'
        print >> output, '\t.section\t.rodata'
        print >> output, '\t.globl\t__gccallshapes'
        print >> output, '__gccallshapes:'
        output.writelines(shapelines)

    def find_functions(self, iterlines):
        functionlines = []
        in_function = False
        for line in iterlines:
            if r_functionstart.match(line):
                assert not in_function, (
                    "missed the end of the previous function")
                yield False, functionlines
                in_function = True
                functionlines = []
            functionlines.append(line)
            if r_functionend.match(line):
                assert in_function, (
                    "missed the start of the current function")
                yield True, functionlines
                in_function = False
                functionlines = []
        assert not in_function, (
            "missed the end of the previous function")
        yield False, functionlines

    def process(self, iterlines, newfile, entrypoint='main', filename='?'):
        for in_function, lines in self.find_functions(iterlines):
            if in_function:
                lines = self.process_function(lines, entrypoint, filename)
            newfile.writelines(lines)
        self.files_seen += 1

    def process_function(self, lines, entrypoint, filename):
        tracker = FunctionGcRootTracker(lines, filetag = self.files_seen)
        tracker.is_main = tracker.funcname == entrypoint
        if self.verbose:
            print >> sys.stderr, '[trackgcroot:%s] %s' % (filename,
                                                          tracker.funcname)
        table = tracker.computegcmaptable(self.verbose)
        if self.verbose > 1:
            for label, state in table:
                print >> sys.stderr, label, '\t', format_callshape(state)
        table = compress_gcmaptable(table)
        if self.shuffle and random.random() < 0.5:
            self.gcmaptable[:0] = table
        else:
            self.gcmaptable.extend(table)
        self.seen_main |= tracker.is_main
        return tracker.lines


class FunctionGcRootTracker(object):

    def __init__(self, lines, filetag=0):
        match = r_functionstart.match(lines[0])
        self.funcname = match.group(1)
        match = r_functionend.match(lines[-1])
        assert self.funcname == match.group(1)
        assert self.funcname == match.group(2)
        self.lines = lines
        self.uses_frame_pointer = False
        self.r_localvar = r_localvarnofp
        self.filetag = filetag
        self.is_main = False

    def computegcmaptable(self, verbose=0):
        self.findlabels()
        self.parse_instructions()
        try:
            if not self.list_call_insns():
                return []
            self.findprevinsns()
            self.findframesize()
            self.fixlocalvars()
            self.trackgcroots()
            self.extend_calls_with_labels()
        finally:
            if verbose > 2:
                self.dump()
        return self.gettable()

    def gettable(self):
        """Returns a list [(label_after_call, callshape_tuple)]
        See format_callshape() for more details about callshape_tuple.
        """
        table = []
        for insn in self.list_call_insns():
            if not hasattr(insn, 'framesize'):
                continue     # calls that never end up reaching a RET
            if self.is_main:
                retaddr = LOC_NOWHERE     # end marker for asmgcroot.py
            elif self.uses_frame_pointer:
                retaddr = frameloc(LOC_EBP_BASED, 4)
            else:
                retaddr = frameloc(LOC_ESP_BASED, insn.framesize)
            shape = [retaddr]
            # the first gcroots are always the ones corresponding to
            # the callee-saved registers
            for reg in CALLEE_SAVE_REGISTERS:
                shape.append(LOC_NOWHERE)
            gcroots = []
            for localvar, tag in insn.gcroots.items():
                if isinstance(localvar, LocalVar):
                    loc = localvar.getlocation(insn.framesize,
                                               self.uses_frame_pointer)
                else:
                    assert localvar in REG2LOC
                    loc = REG2LOC[localvar]
                assert isinstance(loc, int)
                if tag is None:
                    gcroots.append(loc)
                else:
                    regindex = CALLEE_SAVE_REGISTERS.index(tag)
                    shape[1 + regindex] = loc
            if LOC_NOWHERE in shape and not self.is_main:
                reg = CALLEE_SAVE_REGISTERS[shape.index(LOC_NOWHERE) - 1]
                raise AssertionError("cannot track where register %s is saved"
                                     % (reg,))
            gcroots.sort()
            shape.extend(gcroots)
            table.append((insn.global_label, tuple(shape)))
        return table

    def findlabels(self):
        self.labels = {}      # {name: Label()}
        for lineno, line in enumerate(self.lines):
            match = r_label.match(line)
            if match:
                label = match.group(1)
                assert label not in self.labels, "duplicate label"
                self.labels[label] = Label(label, lineno)

    def parse_instructions(self):
        self.insns = [InsnFunctionStart()]
        in_APP = False
        for lineno, line in enumerate(self.lines):
            self.currentlineno = lineno
            insn = []
            match = r_insn.match(line)
            if match:
                if not in_APP:
                    opname = match.group(1)
                    try:
                        meth = getattr(self, 'visit_' + opname)
                    except AttributeError:
                        meth = self.find_missing_visit_method(opname)
                    insn = meth(line)
            elif r_gcroot_marker.match(line):
                insn = self._visit_gcroot_marker(line)
            elif line == '#APP\n':
                in_APP = True
            elif line == '#NO_APP\n':
                in_APP = False
            else:
                match = r_label.match(line)
                if match:
                    insn = self.labels[match.group(1)]
            if isinstance(insn, list):
                self.insns.extend(insn)
            else:
                self.insns.append(insn)
            del self.currentlineno

    def find_missing_visit_method(self, opname):
        # only for operations that are no-ops as far as we are concerned
        prefix = opname
        while prefix not in self.IGNORE_OPS_WITH_PREFIXES:
            prefix = prefix[:-1]
            if not prefix:
                raise UnrecognizedOperation(opname)
        visit_nop = FunctionGcRootTracker.__dict__['visit_nop']
        setattr(FunctionGcRootTracker, 'visit_' + opname, visit_nop)
        return self.visit_nop

    def findprevinsns(self):
        # builds the previous_insns of each Insn.  For Labels, all jumps
        # to them are already registered; all that is left to do is to
        # make each Insn point to the Insn just before it.
        for i in range(len(self.insns)-1):
            previnsn = self.insns[i]
            nextinsn = self.insns[i+1]
            try:
                lst = nextinsn.previous_insns
            except AttributeError:
                lst = nextinsn.previous_insns = []
            if not isinstance(previnsn, InsnStop):
                lst.append(previnsn)

    def list_call_insns(self):
        return [insn for insn in self.insns if isinstance(insn, InsnCall)]

    def findframesize(self):
        # the 'framesize' attached to an instruction is the number of bytes
        # in the frame at this point.  This doesn't count the return address
        # which is the word immediately following the frame in memory.
        # The 'framesize' is set to an odd value if it is only an estimate
        # (see visit_andl()).

        def walker(insn, size_delta):
            check = deltas.setdefault(insn, size_delta)
            assert check == size_delta, (
                "inconsistent frame size at instruction %s" % (insn,))
            if isinstance(insn, InsnStackAdjust):
                size_delta -= insn.delta
            if not hasattr(insn, 'framesize'):
                yield size_delta   # continue walking backwards

        for insn in self.insns:
            if isinstance(insn, (InsnRet, InsnEpilogue, InsnGCROOT)):
                deltas = {}
                self.walk_instructions_backwards(walker, insn, 0)
                size_at_insn = []
                for insn1, delta1 in deltas.items():
                    if hasattr(insn1, 'framesize'):
                        size_at_insn.append(insn1.framesize + delta1)
                assert len(size_at_insn) > 0, (
                    "cannot reach the start of the function??")
                size_at_insn = size_at_insn[0]
                for insn1, delta1 in deltas.items():
                    size_at_insn1 = size_at_insn - delta1
                    if hasattr(insn1, 'framesize'):
                        assert insn1.framesize == size_at_insn1, (
                            "inconsistent frame size at instruction %s" %
                            (insn1,))
                    else:
                        insn1.framesize = size_at_insn1

    def fixlocalvars(self):
        for insn in self.insns:
            if hasattr(insn, 'framesize'):
                for name in insn._locals_:
                    localvar = getattr(insn, name)
                    match = r_localvar_esp.match(localvar)
                    if match:
                        if localvar == '0(%esp)': # for pushl and popl, by
                            hint = None           # default ebp addressing is
                        else:                     # a bit nicer
                            hint = 'esp'
                        ofs_from_esp = int(match.group(1) or '0')
                        localvar = ofs_from_esp - insn.framesize
                        assert localvar != 0    # that's the return address
                        setattr(insn, name, LocalVar(localvar, hint=hint))
                    elif self.uses_frame_pointer:
                        match = r_localvar_ebp.match(localvar)
                        if match:
                            ofs_from_ebp = int(match.group(1) or '0')
                            localvar = ofs_from_ebp - 4
                            assert localvar != 0    # that's the return address
                            setattr(insn, name, LocalVar(localvar, hint='ebp'))

    def trackgcroots(self):

        def walker(insn, loc):
            source = insn.source_of(loc, tag)
            if source is somenewvalue:
                pass   # done
            else:
                yield source

        for insn in self.insns:
            for loc, tag in insn.requestgcroots().items():
                self.walk_instructions_backwards(walker, insn, loc)

    def dump(self):
        for insn in self.insns:
            size = getattr(insn, 'framesize', '?')
            print >> sys.stderr, '%4s  %s' % (size, insn)

    def walk_instructions_backwards(self, walker, initial_insn, initial_state):
        pending = []
        seen = {}
        def schedule(insn, state):
            for previnsn in insn.previous_insns:
                key = previnsn, state
                if key not in seen:
                    seen[key] = True
                    pending.append(key)
        schedule(initial_insn, initial_state)
        while pending:
            insn, state = pending.pop()
            for prevstate in walker(insn, state):
                schedule(insn, prevstate)

    def extend_calls_with_labels(self):
        # walk backwards, because inserting the global labels in self.lines
        # is going to invalidate the lineno of all the InsnCall objects
        # after the current one.
        for call in self.list_call_insns()[::-1]:
            if hasattr(call, 'framesize'):
                self.create_global_label(call)

    def create_global_label(self, call):
        # we need a globally-declared label just after the call.
        # Reuse one if it is already there (e.g. from a previous run of this
        # script); otherwise invent a name and add the label to tracker.lines.
        label = None
        # this checks for a ".globl NAME" followed by "NAME:"
        match = r_globl.match(self.lines[call.lineno+1])
        if match:
            label1 = match.group(1)
            match = r_label.match(self.lines[call.lineno+2])
            if match:
                label2 = match.group(1)
                if label1 == label2:
                    label = label2
        if label is None:
            k = call.lineno
            while 1:
                label = '__gcmap_IN%d_%s_%d' % (self.filetag, self.funcname, k)
                if label not in self.labels:
                    break
                k += 1
            self.labels[label] = None
            self.lines.insert(call.lineno+1, '%s:\n' % (label,))
            self.lines.insert(call.lineno+1, '\t.globl\t%s\n' % (label,))
        call.global_label = label

    # ____________________________________________________________

    def _visit_gcroot_marker(self, line):
        match = r_gcroot_marker.match(line)
        loc = match.group(1)
        return InsnGCROOT(loc)

    def visit_nop(self, line):
        return []

    IGNORE_OPS_WITH_PREFIXES = dict.fromkeys([
        'cmp', 'test', 'set', 'sahf', 'cltd', 'cld', 'std',
        'rep', 'movs', 'lods', 'stos', 'scas', 'cwtl', 'prefetch',
        # floating-point operations cannot produce GC pointers
        'f',
        'cvt',  # sse2
        # arithmetic operations should not produce GC pointers
        'inc', 'dec', 'not', 'neg', 'or', 'and', 'sbb', 'adc',
        'shl', 'shr', 'sal', 'sar', 'rol', 'ror', 'mul', 'imul', 'div', 'idiv',
        # zero-extending moves should not produce GC pointers
        'movz',
        ])

    visit_movb = visit_nop
    visit_movw = visit_nop
    visit_addb = visit_nop
    visit_addw = visit_nop
    visit_subb = visit_nop
    visit_subw = visit_nop
    visit_xorb = visit_nop
    visit_xorw = visit_nop

    def visit_addl(self, line, sign=+1):
        match = r_binaryinsn.match(line)
        target = match.group(2)
        if target == '%esp':
            count = match.group(1)
            if not count.startswith('$'):
                # strange instruction - I've seen 'subl %eax, %esp'
                return InsnCannotFollowEsp()
            return InsnStackAdjust(sign * int(count[1:]))
        elif self.r_localvar.match(target):
            return InsnSetLocal(target)
        else:
            return []

    def visit_subl(self, line):
        return self.visit_addl(line, sign=-1)

    def unary_insn(self, line):
        match = r_unaryinsn.match(line)
        target = match.group(1)
        if self.r_localvar.match(target):
            return InsnSetLocal(target)
        else:
            return []

    def binary_insn(self, line):
        match = r_binaryinsn.match(line)
        if not match:
            raise UnrecognizedOperation(line)
        target = match.group(2)
        if self.r_localvar.match(target):
            return InsnSetLocal(target)
        elif target == '%esp':
            raise UnrecognizedOperation(line)
        else:
            return []

    visit_xorl = binary_insn   # used in "xor reg, reg" to create a NULL GC ptr
    visit_orl = binary_insn
    visit_cmove = binary_insn
    visit_cmovne = binary_insn
    visit_cmovg = binary_insn
    visit_cmovge = binary_insn
    visit_cmovl = binary_insn
    visit_cmovle = binary_insn
    visit_cmova = binary_insn
    visit_cmovae = binary_insn
    visit_cmovb = binary_insn
    visit_cmovbe = binary_insn
    visit_cmovp = binary_insn
    visit_cmovnp = binary_insn
    visit_cmovs = binary_insn
    visit_cmovns = binary_insn
    visit_cmovo = binary_insn
    visit_cmovno = binary_insn

    def visit_andl(self, line):
        match = r_binaryinsn.match(line)
        target = match.group(2)
        if target == '%esp':
            # only for  andl $-16, %esp  used to align the stack in main().
            # The exact amount of adjutment is not known yet, so we use
            # an odd-valued estimate to make sure the real value is not used
            # elsewhere by the FunctionGcRootTracker.
            return InsnCannotFollowEsp()
        else:
            return self.binary_insn(line)

    def visit_leal(self, line):
        match = r_binaryinsn.match(line)
        target = match.group(2)
        if target == '%esp':
            # only for  leal -12(%ebp), %esp  in function epilogues
            source = match.group(1)
            match = r_localvar_ebp.match(source)
            if not match:
                framesize = None    # strange instruction
            else:
                if not self.uses_frame_pointer:
                    raise UnrecognizedOperation('epilogue without prologue')
                ofs_from_ebp = int(match.group(1) or '0')
                assert ofs_from_ebp <= 0
                framesize = 4 - ofs_from_ebp
            return InsnEpilogue(framesize)
        else:
            return self.binary_insn(line)

    def insns_for_copy(self, source, target):
        if source == '%esp' or target == '%esp':
            raise UnrecognizedOperation('%s -> %s' % (source, target))
        elif self.r_localvar.match(target):
            if self.r_localvar.match(source):
                return [InsnCopyLocal(source, target)]
            else:
                return [InsnSetLocal(target)]
        else:
            return []

    def visit_movl(self, line):
        match = r_binaryinsn.match(line)
        source = match.group(1)
        target = match.group(2)
        if source == '%esp' and target == '%ebp':
            return self._visit_prologue()
        elif source == '%ebp' and target == '%esp':
            return self._visit_epilogue()
        return self.insns_for_copy(source, target)

    def visit_pushl(self, line):
        match = r_unaryinsn.match(line)
        source = match.group(1)
        return [InsnStackAdjust(-4)] + self.insns_for_copy(source, '0(%esp)')

    def _visit_pop(self, target):
        return self.insns_for_copy('0(%esp)', target) + [InsnStackAdjust(+4)]

    def visit_popl(self, line):
        match = r_unaryinsn.match(line)
        target = match.group(1)
        return self._visit_pop(target)

    def _visit_prologue(self):
        # for the prologue of functions that use %ebp as frame pointer
        self.uses_frame_pointer = True
        self.r_localvar = r_localvarfp
        return [InsnPrologue()]

    def _visit_epilogue(self):
        if not self.uses_frame_pointer:
            raise UnrecognizedOperation('epilogue without prologue')
        return [InsnEpilogue(4)]

    def visit_leave(self, line):
        return self._visit_epilogue() + self._visit_pop('%ebp')

    def visit_ret(self, line):
        return InsnRet(self.is_main)

    def visit_jmp(self, line):
        match = r_jmp_switch.match(line)
        if match:
            # this is a jmp *Label(%index), used for table-based switches.
            # Assume that the table is just a list of lines looking like
            # .long LABEL or .long 0, ending in a .text or .section .text.hot.
            tablelabel = match.group(1)
            tablelin = self.labels[tablelabel].lineno + 1
            while not r_jmptable_end.match(self.lines[tablelin]):
                match = r_jmptable_item.match(self.lines[tablelin])
                if not match:
                    raise NoPatternMatch(self.lines[tablelin])
                label = match.group(1)
                if label != '0':
                    self.register_jump_to(label)
                tablelin += 1
            return InsnStop()
        if r_unaryinsn_star.match(line):
            # that looks like an indirect tail-call.
            # tail-calls are equivalent to RET for us
            return InsnRet(self.is_main)
        try:
            self.conditional_jump(line)
        except KeyError:
            # label not found: check if it's a tail-call turned into a jump
            match = r_unaryinsn.match(line)
            target = match.group(1)
            assert not target.startswith('.')
            # tail-calls are equivalent to RET for us
            return InsnRet(self.is_main)
        return InsnStop()

    def register_jump_to(self, label):
        self.labels[label].previous_insns.append(self.insns[-1])

    def conditional_jump(self, line):
        match = r_jump.match(line)
        label = match.group(1)
        self.register_jump_to(label)
        return []

    visit_je = conditional_jump
    visit_jne = conditional_jump
    visit_jg = conditional_jump
    visit_jge = conditional_jump
    visit_jl = conditional_jump
    visit_jle = conditional_jump
    visit_ja = conditional_jump
    visit_jae = conditional_jump
    visit_jb = conditional_jump
    visit_jbe = conditional_jump
    visit_jp = conditional_jump
    visit_jnp = conditional_jump
    visit_js = conditional_jump
    visit_jns = conditional_jump
    visit_jo = conditional_jump
    visit_jno = conditional_jump

    def visit_call(self, line):
        match = r_unaryinsn.match(line)
        if match is None:
            assert r_unaryinsn_star.match(line)   # indirect call
        else:
            target = match.group(1)
            if target in FUNCTIONS_NOT_RETURNING:
                return InsnStop()
        return [InsnCall(self.currentlineno),
                InsnSetLocal('%eax')]      # the result is there


class UnrecognizedOperation(Exception):
    pass

class NoPatternMatch(Exception):
    pass

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
    def requestgcroots(self):
        return {}

    def source_of(self, localvar, tag):
        return localvar

class Label(Insn):
    _args_ = ['label', 'lineno']
    def __init__(self, label, lineno):
        self.label = label
        self.lineno = lineno
        self.previous_insns = []   # all insns that jump (or fallthrough) here

class InsnFunctionStart(Insn):
    framesize = 0
    previous_insns = ()
    def __init__(self):
        self.arguments = {}
        for reg in CALLEE_SAVE_REGISTERS:
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

class InsnSetLocal(Insn):
    _args_ = ['target']
    _locals_ = ['target']
    def __init__(self, target):
        self.target = target
    def source_of(self, localvar, tag):
        if localvar == self.target:
            return somenewvalue
        return localvar

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

class InsnStackAdjust(Insn):
    _args_ = ['delta']
    def __init__(self, delta):
        assert delta % 4 == 0
        self.delta = delta

class InsnCannotFollowEsp(InsnStackAdjust):
    def __init__(self):
        self.delta = -7     # use an odd value as marker

class InsnStop(Insn):
    pass

class InsnRet(InsnStop):
    framesize = 0
    def __init__(self, is_main):
        self.is_main = is_main
    def requestgcroots(self):
        if self.is_main:  # no need to track the value of these registers in
            return {}     # the caller function if we are the main()
        else:
            return dict(zip(CALLEE_SAVE_REGISTERS, CALLEE_SAVE_REGISTERS))

class InsnCall(Insn):
    _args_ = ['lineno', 'gcroots']
    def __init__(self, lineno):
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

    def source_of(self, localvar, tag):
        tag1 = self.gcroots.setdefault(localvar, tag)
        assert tag1 == tag, (
            "conflicting entries for InsnCall.gcroots[%s]:\n%r and %r" % (
            localvar, tag1, tag))
        return localvar

class InsnGCROOT(Insn):
    _args_ = ['loc']
    _locals_ = ['loc']
    def __init__(self, loc):
        self.loc = loc
    def requestgcroots(self):
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


FUNCTIONS_NOT_RETURNING = {
    'abort': None,
    '_exit': None,
    '__assert_fail': None,
    }

CALLEE_SAVE_REGISTERS_NOEBP = ['%ebx', '%esi', '%edi']
CALLEE_SAVE_REGISTERS = CALLEE_SAVE_REGISTERS_NOEBP + ['%ebp']

LOC_NOWHERE   = 0
LOC_REG       = 1
LOC_EBP_BASED = 2
LOC_ESP_BASED = 3
LOC_MASK      = 0x03

REG2LOC = {}
for _i, _reg in enumerate(CALLEE_SAVE_REGISTERS):
    REG2LOC[_reg] = LOC_REG | (_i<<2)

def frameloc(base, offset):
    assert base in (LOC_EBP_BASED, LOC_ESP_BASED)
    assert offset % 4 == 0
    return base | offset

# __________ debugging output __________

def format_location(loc):
    # A 'location' is a single number describing where a value is stored
    # across a call.  It can be in one of the CALLEE_SAVE_REGISTERS, or
    # in the stack frame at an address relative to either %esp or %ebp.
    # The last two bits of the location number are used to tell the cases
    # apart; see format_location().
    kind = loc & LOC_MASK
    if kind == LOC_NOWHERE:
        return '?'
    elif kind == LOC_REG:
        reg = loc >> 2
        assert 0 <= reg <= 3
        return CALLEE_SAVE_REGISTERS[reg]
    else:
        if kind == LOC_EBP_BASED:
            result = '(%ebp)'
        else:
            result = '(%esp)'
        offset = loc & ~ LOC_MASK
        if offset != 0:
            result = str(offset) + result
        return result

def format_callshape(shape):
    # A 'call shape' is a tuple of locations in the sense of format_location().
    # They describe where in a function frame interesting values are stored,
    # when this function executes a 'call' instruction.
    #
    #   shape[0] is the location that stores the fn's own return address
    #            (not the return address for the currently executing 'call')
    #   shape[1] is where the fn saved its own caller's %ebx value
    #   shape[2] is where the fn saved its own caller's %esi value
    #   shape[3] is where the fn saved its own caller's %edi value
    #   shape[4] is where the fn saved its own caller's %ebp value
    #   shape[>=5] are GC roots: where the fn has put its local GCPTR vars
    #
    assert isinstance(shape, tuple)
    assert len(shape) >= 5
    result = [format_location(loc) for loc in shape]
    return '{%s | %s | %s}' % (result[0],
                               ', '.join(result[1:5]),
                               ', '.join(result[5:]))

# __________ table compression __________

def compress_gcmaptable(table):
    # Compress ranges table[i:j] of entries with the same state
    # into a single entry whose label is the start of the range.
    # The last element in the table is never compressed in this
    # way for debugging reasons, to avoid that a random address
    # in memory gets mapped to the last element in the table
    # just because it's the closest address.
    # To be on the safe side, compress_gcmaptable() should be called
    # after each function processed -- otherwise the result depends on
    # the linker not rearranging the functions in memory, which is
    # fragile (and wrong e.g. with "make profopt").
    i = 0
    limit = len(table) - 1     # only process entries table[:limit]
    while i < len(table):
        label1, state = table[i]
        is_range = False
        j = i + 1
        while j < limit and table[j][1] == state:
            is_range = True
            j += 1
        # now all entries in table[i:j] have the same state
        yield (label1, state, is_range)
        i = j

def compress_callshape(shape):
    # For a single shape, this turns the list of integers into a list of
    # bytes and reverses the order of the entries.  The length is
    # encoded by inserting a 0 marker after the gc roots coming from
    # shape[5:] and before the 5 values coming from shape[4] to
    # shape[0].  In practice it seems that shapes contain many integers
    # whose value is up to a few thousands, which the algorithm below
    # compresses down to 2 bytes.  Very small values compress down to a
    # single byte.
    assert len(shape) >= 5
    shape = list(shape)
    assert 0 not in shape[5:]
    shape.insert(5, 0)
    result = []
    for loc in shape:
        if loc < 0:
            loc = (-loc) * 2 - 1
        else:
            loc = loc * 2
        flag = 0
        while loc >= 0x80:
            result.append(int(loc & 0x7F) | flag)
            flag = 0x80
            loc >>= 7
        result.append(int(loc) | flag)
    result.reverse()
    return result

def decompress_callshape(bytes):
    # For tests.  This logic is copied in asmgcroot.py.
    result = []
    n = 0
    while n < len(bytes):
        value = 0
        while True:
            b = bytes[n]
            n += 1
            value += b
            if b < 0x80:
                break
            value = (value - 0x80) << 7
        if value & 1:
            value = ~ value
        value = value >> 1
        result.append(value)
    result.reverse()
    assert result[5] == 0
    del result[5]
    return result


if __name__ == '__main__':
    verbose = 1
    shuffle = False
    output_raw_table = False
    while len(sys.argv) > 1:
        if sys.argv[1] == '-v':
            del sys.argv[1]
            verbose = sys.maxint
        elif sys.argv[1] == '-r':
            del sys.argv[1]
            shuffle = True
        elif sys.argv[1] == '-t':
            del sys.argv[1]
            output_raw_table = True
        else:
            break
    tracker = GcRootTracker(verbose=verbose, shuffle=shuffle)
    for fn in sys.argv[1:]:
        tmpfn = fn + '.TMP'
        f = open(fn, 'r')
        firstline = f.readline()
        f.seek(0)
        if firstline.startswith('seen_main = '):
            tracker.reload_raw_table(f)
            f.close()
        else:
            g = open(tmpfn, 'w')
            tracker.process(f, g, filename=fn)
            f.close()
            g.close()
            os.unlink(fn)
            os.rename(tmpfn, fn)
            if output_raw_table:
                tracker.dump_raw_table(sys.stdout)
                tracker.clear()
    if not output_raw_table:
        tracker.dump(sys.stdout)
