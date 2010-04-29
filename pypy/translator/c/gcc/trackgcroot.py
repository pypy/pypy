#! /usr/bin/env python
import autopath
import re, sys, os, random

from pypy.translator.c.gcc.instruction import Insn, Label, InsnCall, InsnRet
from pypy.translator.c.gcc.instruction import InsnFunctionStart, InsnStop
from pypy.translator.c.gcc.instruction import InsnSetLocal, InsnCopyLocal
from pypy.translator.c.gcc.instruction import InsnPrologue, InsnEpilogue
from pypy.translator.c.gcc.instruction import InsnGCROOT
from pypy.translator.c.gcc.instruction import InsnStackAdjust
from pypy.translator.c.gcc.instruction import InsnCannotFollowEsp
from pypy.translator.c.gcc.instruction import LocalVar, somenewvalue
from pypy.translator.c.gcc.instruction import frameloc_esp, frameloc_ebp
from pypy.translator.c.gcc.instruction import LOC_REG, LOC_NOWHERE, LOC_MASK
from pypy.translator.c.gcc.instruction import LOC_EBP_PLUS, LOC_EBP_MINUS
from pypy.translator.c.gcc.instruction import LOC_ESP_PLUS

class FunctionGcRootTracker(object):
    skip = 0

    @classmethod
    def init_regexp(cls):
        cls.r_label         = re.compile(cls.LABEL+"[:]\s*$")
        cls.r_globl         = re.compile(r"\t[.]globl\t"+cls.LABEL+"\s*$")
        cls.r_globllabel    = re.compile(cls.LABEL+r"=[.][+]%d\s*$"%cls.OFFSET_LABELS)

        cls.r_insn          = re.compile(r"\t([a-z]\w*)\s")
        cls.r_unaryinsn     = re.compile(r"\t[a-z]\w*\s+("+cls.OPERAND+")\s*$")
        cls.r_binaryinsn    = re.compile(r"\t[a-z]\w*\s+(?P<source>"+cls.OPERAND+"),\s*(?P<target>"+cls.OPERAND+")\s*$")

        cls.r_jump          = re.compile(r"\tj\w+\s+"+cls.LABEL+"\s*$")
        cls.r_jmp_switch    = re.compile(r"\tjmp\t[*]"+cls.LABEL+"[(]")
        cls.r_jmp_source    = re.compile(r"\d*[(](%[\w]+)[,)]")

    def __init__(self, funcname, lines, filetag=0):
        self.funcname = funcname
        self.lines = lines
        self.uses_frame_pointer = False
        self.r_localvar = self.r_localvarnofp
        self.filetag = filetag
        # a "stack bottom" function is either main() or a callback from C code
        self.is_stack_bottom = False

    def computegcmaptable(self, verbose=0):
        self.findlabels()
        self.parse_instructions()
        try:
            self.find_noncollecting_calls()
            if not self.list_collecting_call_insns():
                return []
            self.findframesize()
            self.fixlocalvars()
            self.trackgcroots()
            self.extend_calls_with_labels()
        finally:
            if verbose > 2:
                self.dump()
        return self.gettable()

    def replace_symbols(self, operand):
        return operand

    def gettable(self):
        """Returns a list [(label_after_call, callshape_tuple)]
        See format_callshape() for more details about callshape_tuple.
        """
        table = []
        for insn in self.list_collecting_call_insns():
            if not hasattr(insn, 'framesize'):
                continue     # calls that never end up reaching a RET
            if self.is_stack_bottom:
                retaddr = LOC_NOWHERE     # end marker for asmgcroot.py
            elif self.uses_frame_pointer:
                retaddr = frameloc_ebp(4)
            else:
                retaddr = frameloc_esp(insn.framesize)
            shape = [retaddr]
            # the first gcroots are always the ones corresponding to
            # the callee-saved registers
            for reg in self.CALLEE_SAVE_REGISTERS:
                shape.append(LOC_NOWHERE)
            gcroots = []
            for localvar, tag in insn.gcroots.items():
                if isinstance(localvar, LocalVar):
                    loc = localvar.getlocation(insn.framesize,
                                               self.uses_frame_pointer)
                elif localvar in self.REG2LOC:
                    loc = self.REG2LOC[localvar]
                else:
                    assert False, "%s: %s" % (self.funcname,
                                              localvar)
                assert isinstance(loc, int)
                if tag is None:
                    gcroots.append(loc)
                else:
                    regindex = self.CALLEE_SAVE_REGISTERS.index(tag)
                    shape[1 + regindex] = loc
            if LOC_NOWHERE in shape and not self.is_stack_bottom:
                reg = self.CALLEE_SAVE_REGISTERS[shape.index(LOC_NOWHERE) - 1]
                raise AssertionError("cannot track where register %s is saved"
                                     % (reg,))
            gcroots.sort()
            shape.extend(gcroots)
            table.append((insn.global_label, tuple(shape)))
        return table

    def findlabels(self):
        self.labels = {}      # {name: Label()}
        for lineno, line in enumerate(self.lines):
            match = self.r_label.match(line)
            label = None
            if match:
                label = match.group(1)
            else:
                # labels used by: j* NNNf
                match = self.r_rel_label.match(line)
                if match:
                    label = "rel %d" % lineno
            if label:
                assert label not in self.labels, "duplicate label: %s" % label
                self.labels[label] = Label(label, lineno)

    def find_noncollecting_calls(self):
        cannot_collect = self.CANNOT_COLLECT.copy()
        for line in self.lines:
            match = self.r_gcnocollect_marker.search(line)
            if match:
                name = match.group(1)
                cannot_collect[name] = True
        #
        if self.format in ('darwin', 'mingw32', 'msvc'):
            self.cannot_collect = dict.fromkeys(
                ['_' + name for name in cannot_collect])
        else:
            self.cannot_collect = cannot_collect

    def append_instruction(self, insn):
        # Add the instruction to the list, and link it to the previous one.
        previnsn = self.insns[-1]
        self.insns.append(insn)

        try:
            lst = insn.previous_insns
        except AttributeError:
            lst = insn.previous_insns = []
        if not isinstance(previnsn, InsnStop):
            lst.append(previnsn)

    def parse_instructions(self):
        self.insns = [InsnFunctionStart(self.CALLEE_SAVE_REGISTERS)]
        ignore_insns = False
        for lineno, line in enumerate(self.lines):
            if lineno < self.skip:
                continue
            self.currentlineno = lineno
            insn = []
            match = self.r_insn.match(line)

            if self.r_bottom_marker.match(line):
                self.is_stack_bottom = True
            elif match:
                if not ignore_insns:
                    opname = match.group(1)
                    try:
                        meth = getattr(self, 'visit_' + opname)
                    except AttributeError:
                        self.find_missing_visit_method(opname)
                        meth = getattr(self, 'visit_' + opname)
                    line = line.rsplit(';', 1)[0]
                    insn = meth(line)
            elif self.r_gcroot_marker.match(line):
                insn = self._visit_gcroot_marker(line)
            elif line == '\t/* ignore_in_trackgcroot */\n':
                ignore_insns = True
            elif line == '\t/* end_ignore_in_trackgcroot */\n':
                ignore_insns = False
            else:
                match = self.r_label.match(line)
                if match:
                    insn = self.labels[match.group(1)]

            if isinstance(insn, list):
                for i in insn:
                    self.append_instruction(i)
            else:
                self.append_instruction(insn)

        del self.currentlineno

    @classmethod
    def find_missing_visit_method(cls, opname):
        # only for operations that are no-ops as far as we are concerned
        prefix = opname
        while prefix not in cls.IGNORE_OPS_WITH_PREFIXES:
            prefix = prefix[:-1]
            if not prefix:
                raise UnrecognizedOperation(opname)
        setattr(cls, 'visit_' + opname, cls.visit_nop)

    def list_collecting_call_insns(self):
        return [insn for insn in self.insns if isinstance(insn, InsnCall)
                     if insn.name not in self.cannot_collect]

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
                if not size_at_insn:
                    continue
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
        def fixvar(localvar):
            if localvar is None:
                return None
            elif isinstance(localvar, (list, tuple)):
                return [fixvar(var) for var in localvar]

            match = self.r_localvar_esp.match(localvar)
            if match:
                if localvar == self.TOP_OF_STACK: # for pushl and popl, by
                    hint = None                   # default ebp addressing is
                else:                             # a bit nicer
                    hint = 'esp'
                ofs_from_esp = int(match.group(1) or '0')
                if self.format == 'msvc':
                    ofs_from_esp += int(match.group(2) or '0')
                localvar = ofs_from_esp - insn.framesize
                assert localvar != 0    # that's the return address
                return LocalVar(localvar, hint=hint)
            elif self.uses_frame_pointer:
                match = self.r_localvar_ebp.match(localvar)
                if match:
                    ofs_from_ebp = int(match.group(1) or '0')
                    if self.format == 'msvc':
                        ofs_from_ebp += int(match.group(2) or '0')
                    localvar = ofs_from_ebp - 4
                    assert localvar != 0    # that's the return address
                    return LocalVar(localvar, hint='ebp')
            return localvar

        for insn in self.insns:
            if not hasattr(insn, 'framesize'):
                continue
            for name in insn._locals_:
                localvar = getattr(insn, name)
                setattr(insn, name, fixvar(localvar))

    def trackgcroots(self):

        def walker(insn, loc):
            source = insn.source_of(loc, tag)
            if source is somenewvalue:
                pass   # done
            else:
                yield source

        for insn in self.insns:
            for loc, tag in insn.requestgcroots(self).items():
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
        for call in self.list_collecting_call_insns()[::-1]:
            if hasattr(call, 'framesize'):
                self.create_global_label(call)

    def create_global_label(self, call):
        # we need a globally-declared label just after the call.
        # Reuse one if it is already there (e.g. from a previous run of this
        # script); otherwise invent a name and add the label to tracker.lines.
        label = None
        # this checks for a ".globl NAME" followed by "NAME:"
        match = self.r_globl.match(self.lines[call.lineno+1])
        if match:
            label1 = match.group(1)
            match = self.r_globllabel.match(self.lines[call.lineno+2])
            if match:
                label2 = match.group(1)
                if label1 == label2:
                    label = label2
        if label is None:
            k = call.lineno
            if self.format == 'msvc':
                # Some header files (ws2tcpip.h) define STDCALL functions
                funcname = self.funcname.split('@')[0]
            else:
                funcname = self.funcname
            while 1:
                label = '__gcmap_%s__%s_%d' % (self.filetag, funcname, k)
                if label not in self.labels:
                    break
                k += 1
            self.labels[label] = None
            if self.format == 'msvc':
                self.lines.insert(call.lineno+1, '%s::\n' % (label,))
                self.lines.insert(call.lineno+1, 'PUBLIC\t%s\n' % (label,))
            else:
                # These global symbols are not directly labels pointing to the
                # code location because such global labels in the middle of
                # functions confuse gdb.  Instead, we add to the global symbol's
                # value a big constant, which is subtracted again when we need
                # the original value for gcmaptable.s.  That's a hack.
                self.lines.insert(call.lineno+1, '%s=.+%d\n' % (label,
                                                                self.OFFSET_LABELS))
                self.lines.insert(call.lineno+1, '\t.globl\t%s\n' % (label,))
        call.global_label = label

    # ____________________________________________________________

    CANNOT_COLLECT = {    # some of the most used functions that cannot collect
        'pypy_debug_catch_fatal_exception': None,
        'RPyAbort': None,
        'RPyAssertFailed': None,
        }

    def _visit_gcroot_marker(self, line):
        match = self.r_gcroot_marker.match(line)
        loc = match.group(1)
        return InsnGCROOT(self.replace_symbols(loc))

    def visit_nop(self, line):
        return []

    IGNORE_OPS_WITH_PREFIXES = dict.fromkeys([
        'cmp', 'test', 'set', 'sahf', 'lahf', 'cltd', 'cld', 'std',
        'rep', 'movs', 'lods', 'stos', 'scas', 'cwtl', 'prefetch',
        # floating-point operations cannot produce GC pointers
        'f',
        'cvt', 'ucomi', 'comi', 'subs', 'subp' , 'adds', 'addp', 'xorp',
        'movap', 'movd', 'movlp', 'sqrtsd',
        'mins', 'minp', 'maxs', 'maxp', 'unpck', 'pxor', 'por', # sse2
        # arithmetic operations should not produce GC pointers
        'inc', 'dec', 'not', 'neg', 'or', 'and', 'sbb', 'adc',
        'shl', 'shr', 'sal', 'sar', 'rol', 'ror', 'mul', 'imul', 'div', 'idiv',
        'bswap', 'bt', 'rdtsc',
        # zero-extending moves should not produce GC pointers
        'movz',
        # quadword operations
        'movq',
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
        match = self.r_binaryinsn.match(line)
        source = match.group("source")
        target = match.group("target")
        if target == self.ESP:
            count = self.extract_immediate(source)
            if count is None:
                # strange instruction - I've seen 'subl %eax, %esp'
                return InsnCannotFollowEsp()
            return InsnStackAdjust(sign * count)
        elif self.r_localvar.match(target):
            return InsnSetLocal(target, [source, target])
        else:
            return []

    def visit_subl(self, line):
        return self.visit_addl(line, sign=-1)

    def unary_insn(self, line):
        match = self.r_unaryinsn.match(line)
        target = match.group(1)
        if self.r_localvar.match(target):
            return InsnSetLocal(target)
        else:
            return []

    def binary_insn(self, line):
        match = self.r_binaryinsn.match(line)
        if not match:
            raise UnrecognizedOperation(line)
        source = match.group("source")
        target = match.group("target")
        if self.r_localvar.match(target):
            return InsnSetLocal(target, [source])
        elif target == self.ESP:
            raise UnrecognizedOperation(line)
        else:
            return []

    visit_xorl = binary_insn   # used in "xor reg, reg" to create a NULL GC ptr
    visit_orl = binary_insn
    # The various cmov* operations
    for name in '''
        e ne g ge l le a ae b be p np s ns o no
        '''.split():
        locals()['visit_cmov' + name] = binary_insn
        locals()['visit_cmov' + name + 'l'] = binary_insn

    def visit_andl(self, line):
        match = self.r_binaryinsn.match(line)
        target = match.group("target")
        if target == self.ESP:
            # only for  andl $-16, %esp  used to align the stack in main().
            # The exact amount of adjutment is not known yet, so we use
            # an odd-valued estimate to make sure the real value is not used
            # elsewhere by the FunctionGcRootTracker.
            return InsnCannotFollowEsp()
        else:
            return self.binary_insn(line)

    visit_and = visit_andl

    def visit_leal(self, line):
        match = self.r_binaryinsn.match(line)
        target = match.group("target")
        if target == self.ESP:
            # only for  leal -12(%ebp), %esp  in function epilogues
            source = match.group("source")
            match = self.r_localvar_ebp.match(source)
            if match:
                if not self.uses_frame_pointer:
                    raise UnrecognizedOperation('epilogue without prologue')
                ofs_from_ebp = int(match.group(1) or '0')
                assert ofs_from_ebp <= 0
                framesize = 4 - ofs_from_ebp
            else:
                match = self.r_localvar_esp.match(source)
                # leal 12(%esp), %esp
                if match:
                    return InsnStackAdjust(int(match.group(1)))

                framesize = None    # strange instruction
            return InsnEpilogue(framesize)
        else:
            return self.binary_insn(line)

    def insns_for_copy(self, source, target):
        source = self.replace_symbols(source)
        target = self.replace_symbols(target)
        if source == self.ESP or target == self.ESP:
            raise UnrecognizedOperation('%s -> %s' % (source, target))
        elif self.r_localvar.match(target):
            if self.r_localvar.match(source):
                return [InsnCopyLocal(source, target)]
            else:
                return [InsnSetLocal(target, [source])]
        else:
            return []

    def visit_movl(self, line):
        match = self.r_binaryinsn.match(line)
        source = match.group("source")
        target = match.group("target")
        if source == self.ESP and target == self.EBP:
            return self._visit_prologue()
        elif source == self.EBP and target == self.ESP:
            return self._visit_epilogue()
        if source == self.ESP and self.funcname.startswith('VALGRIND_'):
            return []     # in VALGRIND_XXX functions, there is a dummy-looking
                          # mov %esp, %eax.  Shows up only when compiling with
                          # gcc -fno-unit-at-a-time.
        return self.insns_for_copy(source, target)

    visit_mov = visit_movl

    def visit_pushl(self, line):
        match = self.r_unaryinsn.match(line)
        source = match.group(1)
        return [InsnStackAdjust(-4)] + self.insns_for_copy(source, self.TOP_OF_STACK)

    def visit_pushw(self, line):
        return [InsnStackAdjust(-2)]   # rare but not impossible

    def _visit_pop(self, target):
        return self.insns_for_copy(self.TOP_OF_STACK, target) + [InsnStackAdjust(+4)]

    def visit_popl(self, line):
        match = self.r_unaryinsn.match(line)
        target = match.group(1)
        return self._visit_pop(target)

    def _visit_prologue(self):
        # for the prologue of functions that use %ebp as frame pointer
        self.uses_frame_pointer = True
        self.r_localvar = self.r_localvarfp
        return [InsnPrologue()]

    def _visit_epilogue(self):
        if not self.uses_frame_pointer:
            raise UnrecognizedOperation('epilogue without prologue')
        return [InsnEpilogue(4)]

    def visit_leave(self, line):
        return self._visit_epilogue() + self._visit_pop(self.EBP)

    def visit_ret(self, line):
        return InsnRet(self.CALLEE_SAVE_REGISTERS)

    def visit_jmp(self, line):
        tablelabels = []
        match = self.r_jmp_switch.match(line)
        if match:
            # this is a jmp *Label(%index), used for table-based switches.
            # Assume that the table is just a list of lines looking like
            # .long LABEL or .long 0, ending in a .text or .section .text.hot.
            tablelabels.append(match.group(1))
        elif self.r_unaryinsn_star.match(line):
            # maybe a jmp similar to the above, but stored in a
            # registry:
            #     movl L9341(%eax), %eax
            #     jmp *%eax
            operand = self.r_unaryinsn_star.match(line).group(1)
            def walker(insn, locs):
                sources = []
                for loc in locs:
                    for s in insn.all_sources_of(loc):
                        # if the source looks like 8(%eax,%edx,4)
                        # %eax is the real source, %edx is an offset.
                        match = self.r_jmp_source.match(s)
                        if match and not self.r_localvar_esp.match(s):
                            sources.append(match.group(1))
                        else:
                            sources.append(s)
                for source in sources:
                    label_match = re.compile(self.LABEL).match(source)
                    if label_match:
                        tablelabels.append(label_match.group(0))
                        return
                yield tuple(sources)
            insn = InsnStop()
            insn.previous_insns = [self.insns[-1]]
            self.walk_instructions_backwards(walker, insn, (operand,))

            # Remove probable tail-calls
            tablelabels = [label for label in tablelabels
                           if label in self.labels]
        assert len(tablelabels) <= 1
        if tablelabels:
            tablelin = self.labels[tablelabels[0]].lineno + 1
            while not self.r_jmptable_end.match(self.lines[tablelin]):
                # skip empty lines
                if (not self.lines[tablelin].strip()
                    or self.lines[tablelin].startswith(';')):
                    tablelin += 1
                    continue
                match = self.r_jmptable_item.match(self.lines[tablelin])
                if not match:
                    raise NoPatternMatch(repr(self.lines[tablelin]))
                label = match.group(1)
                if label != '0':
                    self.register_jump_to(label)
                tablelin += 1
            return InsnStop()
        if self.r_unaryinsn_star.match(line):
            # that looks like an indirect tail-call.
            # tail-calls are equivalent to RET for us
            return InsnRet(self.CALLEE_SAVE_REGISTERS)
        try:
            self.conditional_jump(line)
        except KeyError:
            # label not found: check if it's a tail-call turned into a jump
            match = self.r_unaryinsn.match(line)
            target = match.group(1)
            assert not target.startswith('.')
            # tail-calls are equivalent to RET for us
            return InsnRet(self.CALLEE_SAVE_REGISTERS)
        return InsnStop()

    def register_jump_to(self, label):
        if not isinstance(self.insns[-1], InsnStop):
            self.labels[label].previous_insns.append(self.insns[-1])

    def conditional_jump(self, line):
        match = self.r_jump.match(line)
        if not match:
            match = self.r_jump_rel_label.match(line)
            if not match:
                raise UnrecognizedOperation(line)
            # j* NNNf
            label = match.group(1)
            label += ":"
            i = self.currentlineno + 1
            while True:
                if self.lines[i].startswith(label):
                    label = "rel %d" % i
                    break
                i += 1
        else:
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
    visit_jc = conditional_jump
    visit_jnc = conditional_jump

    def visit_xchgl(self, line):
        # only support the format used in VALGRIND_DISCARD_TRANSLATIONS
        # which is to use a marker no-op "xchgl %ebx, %ebx"
        match = self.r_binaryinsn.match(line)
        source = match.group("source")
        target = match.group("target")
        if source == target:
            return []
        raise UnrecognizedOperation(line)

    def visit_call(self, line):
        match = self.r_unaryinsn.match(line)

        if match is None:
            assert self.r_unaryinsn_star.match(line)   # indirect call
            return [InsnCall('<indirect>', self.currentlineno),
                    InsnSetLocal(self.EAX)]      # the result is there

        target = match.group(1)

        if self.format in ('msvc',):
            # On win32, the address of a foreign function must be
            # computed, the optimizer may store it in a register.  We
            # could ignore this, except when the function need special
            # processing (not returning, __stdcall...)
            def find_register(target):
                reg = []
                def walker(insn, locs):
                    sources = []
                    for loc in locs:
                        for s in insn.all_sources_of(loc):
                            sources.append(s)
                    for source in sources:
                        m = re.match("DWORD PTR " + self.LABEL, source)
                        if m:
                            reg.append(m.group(1))
                    if reg:
                        return
                    yield tuple(sources)
                insn = InsnStop()
                insn.previous_insns = [self.insns[-1]]
                self.walk_instructions_backwards(walker, insn, (target,))
                return reg

            if match and self.r_localvarfp.match(target):
                sources = find_register(target)
                if sources:
                    target, = sources

        if target in self.FUNCTIONS_NOT_RETURNING:
            return [InsnStop(), InsnCannotFollowEsp()]
        if self.format == 'mingw32' and target == '__alloca':
            # in functions with large stack requirements, windows
            # needs a call to _alloca(), to turn reserved pages
            # into committed memory.
            # With mingw32 gcc at least, %esp is not used before
            # this call.  So we don't bother to compute the exact
            # stack effect.
            return [InsnCannotFollowEsp()]
        if target in self.labels:
            lineoffset = self.labels[target].lineno - self.currentlineno
            if lineoffset >= 0:
                assert  lineoffset in (1,2)
                return [InsnStackAdjust(-4)]

        insns = [InsnCall(target, self.currentlineno),
                 InsnSetLocal(self.EAX)]      # the result is there
        if self.format in ('mingw32', 'msvc'):
            # handle __stdcall calling convention:
            # Stack cleanup is performed by the called function,
            # Function name is decorated with "@N" where N is the stack size
            if '@' in target and not target.startswith('@'):
                insns.append(InsnStackAdjust(int(target.rsplit('@', 1)[1])))
            # Some (intrinsic?) functions use the "fastcall" calling convention
            # XXX without any declaration, how can we guess the stack effect?
            if target in ['__alldiv', '__allrem', '__allmul', '__alldvrm']:
                insns.append(InsnStackAdjust(16))
        return insns


class ElfFunctionGcRootTracker(FunctionGcRootTracker):
    format = 'elf'

    ESP     = '%esp'
    EBP     = '%ebp'
    EAX     = '%eax'
    CALLEE_SAVE_REGISTERS = ['%ebx', '%esi', '%edi', '%ebp']
    REG2LOC = dict((_reg, LOC_REG | ((_i+1)<<2))
                   for _i, _reg in enumerate(CALLEE_SAVE_REGISTERS))
    OPERAND = r'(?:[-\w$%+.:@"]+(?:[(][\w%,]+[)])?|[(][\w%,]+[)])'
    LABEL   = r'([a-zA-Z_$.][a-zA-Z0-9_$@.]*)'
    OFFSET_LABELS   = 2**30
    TOP_OF_STACK = '0(%esp)'

    r_functionstart = re.compile(r"\t.type\s+"+LABEL+",\s*[@]function\s*$")
    r_functionend   = re.compile(r"\t.size\s+"+LABEL+",\s*[.]-"+LABEL+"\s*$")
    LOCALVAR        = r"%eax|%edx|%ecx|%ebx|%esi|%edi|%ebp|\d*[(]%esp[)]"
    LOCALVARFP      = LOCALVAR + r"|-?\d*[(]%ebp[)]"
    r_localvarnofp  = re.compile(LOCALVAR)
    r_localvarfp    = re.compile(LOCALVARFP)
    r_localvar_esp  = re.compile(r"(\d*)[(]%esp[)]")
    r_localvar_ebp  = re.compile(r"(-?\d*)[(]%ebp[)]")

    r_rel_label      = re.compile(r"(\d+):\s*$")
    r_jump_rel_label = re.compile(r"\tj\w+\s+"+"(\d+)f"+"\s*$")

    r_unaryinsn_star= re.compile(r"\t[a-z]\w*\s+[*]("+OPERAND+")\s*$")
    r_jmptable_item = re.compile(r"\t.long\t"+LABEL+"(-\"[A-Za-z0-9$]+\")?\s*$")
    r_jmptable_end  = re.compile(r"\t.text|\t.section\s+.text|\t\.align|"+LABEL)

    r_gcroot_marker = re.compile(r"\t/[*] GCROOT ("+LOCALVARFP+") [*]/")
    r_gcnocollect_marker = re.compile(r"\t/[*] GC_NOCOLLECT ("+OPERAND+") [*]/")
    r_bottom_marker = re.compile(r"\t/[*] GC_STACK_BOTTOM [*]/")

    FUNCTIONS_NOT_RETURNING = {
        'abort': None,
        '_exit': None,
        '__assert_fail': None,
        '___assert_rtn': None,
        'L___assert_rtn$stub': None,
        'L___eprintf$stub': None,
        }

    def __init__(self, lines, filetag=0):
        match = self.r_functionstart.match(lines[0])
        funcname = match.group(1)
        match = self.r_functionend.match(lines[-1])
        assert funcname == match.group(1)
        assert funcname == match.group(2)
        super(ElfFunctionGcRootTracker, self).__init__(
            funcname, lines, filetag)

    def extract_immediate(self, value):
        if not value.startswith('$'):
            return None
        return int(value[1:])

ElfFunctionGcRootTracker.init_regexp()

class DarwinFunctionGcRootTracker(ElfFunctionGcRootTracker):
    format = 'darwin'

    r_functionstart = re.compile(r"_(\w+):\s*$")
    OFFSET_LABELS   = 0

    def __init__(self, lines, filetag=0):
        match = self.r_functionstart.match(lines[0])
        funcname = '_' + match.group(1)
        FunctionGcRootTracker.__init__(self, funcname, lines, filetag)

class Mingw32FunctionGcRootTracker(DarwinFunctionGcRootTracker):
    format = 'mingw32'

    FUNCTIONS_NOT_RETURNING = {
        '_abort': None,
        '_exit': None,
        '__assert': None,
        }

class MsvcFunctionGcRootTracker(FunctionGcRootTracker):
    format = 'msvc'
    ESP = 'esp'
    EBP = 'ebp'
    EAX = 'eax'
    CALLEE_SAVE_REGISTERS = ['ebx', 'esi', 'edi', 'ebp']
    REG2LOC = dict((_reg, LOC_REG | ((_i+1)<<2))
                   for _i, _reg in enumerate(CALLEE_SAVE_REGISTERS))
    TOP_OF_STACK = 'DWORD PTR [esp]'

    OPERAND = r'(?:(:?WORD|DWORD|BYTE) PTR |OFFSET )?[_\w?:@$]*(?:[-+0-9]+)?(:?\[[-+*\w0-9]+\])?'
    LABEL   = r'([a-zA-Z_$@.][a-zA-Z0-9_$@.]*)'
    OFFSET_LABELS = 0

    r_segmentstart  = re.compile(r"[_A-Z]+\tSEGMENT$")
    r_segmentend    = re.compile(r"[_A-Z]+\tENDS$")
    r_functionstart = re.compile(r"; Function compile flags: ")
    r_codestart     = re.compile(LABEL+r"\s+PROC\s*(:?;.+)?\n$")
    r_functionend   = re.compile(LABEL+r"\s+ENDP\s*$")
    r_symboldefine =  re.compile(r"([_A-Za-z0-9$]+) = ([-0-9]+)\s*;.+\n")

    LOCALVAR        = r"eax|edx|ecx|ebx|esi|edi|ebp|DWORD PTR [-+]?\d*\[esp[-+]?\d*\]"
    LOCALVARFP      = LOCALVAR + r"|DWORD PTR -?\d*\[ebp\]"
    r_localvarnofp  = re.compile(LOCALVAR)
    r_localvarfp    = re.compile(LOCALVARFP)
    r_localvar_esp  = re.compile(r"DWORD PTR ([-+]?\d+)?\[esp([-+]?\d+)?\]")
    r_localvar_ebp  = re.compile(r"DWORD PTR ([-+]?\d+)?\[ebp([-+]?\d+)?\]")

    r_rel_label      = re.compile(r"$1") # never matches
    r_jump_rel_label = re.compile(r"$1") # never matches

    r_unaryinsn_star= re.compile(r"\t[a-z]\w*\s+DWORD PTR ("+OPERAND+")\s*$")
    r_jmptable_item = re.compile(r"\tDD\t"+LABEL+"(-\"[A-Za-z0-9$]+\")?\s*$")
    r_jmptable_end  = re.compile(r"[^\t\n;]")

    r_gcroot_marker = re.compile(r"$1") # never matches
    r_gcroot_marker_var = re.compile(r"DWORD PTR .+_constant_always_one_.+pypy_asm_gcroot")
    r_gcnocollect_marker = re.compile(r"\spypy_asm_gc_nocollect\(("+OPERAND+")\);")
    r_bottom_marker = re.compile(r"; .+\tpypy_asm_stack_bottom\(\);")

    FUNCTIONS_NOT_RETURNING = {
        '_abort': None,
        '__exit': None,
        '__assert': None,
        '__wassert': None,
        '__imp__abort': None,
        '__imp___wassert': None,
        'DWORD PTR __imp__abort': None,
        'DWORD PTR __imp___wassert': None,
        }

    @classmethod
    def init_regexp(cls):
        super(MsvcFunctionGcRootTracker, cls).init_regexp()
        cls.r_binaryinsn    = re.compile(r"\t[a-z]\w*\s+(?P<target>"+cls.OPERAND+r"),\s*(?P<source>"+cls.OPERAND+r")\s*(?:;.+)?$")
        cls.r_jump = re.compile(r"\tj\w+\s+(?:SHORT |DWORD PTR )?"+cls.LABEL+"\s*$")

    def __init__(self, lines, filetag=0):
        self.defines = {}
        for i, line in enumerate(lines):
            if self.r_symboldefine.match(line):
                match = self.r_symboldefine.match(line)
                name = match.group(1)
                value = int(match.group(2))
                self.defines[name] = value
                continue

            match = self.r_codestart.match(line)
            if match:
                self.skip = i
                break

        funcname = match.group(1)
        super(MsvcFunctionGcRootTracker, self).__init__(
            funcname, lines, filetag)

    def replace_symbols(self, operand):
        for name, value in self.defines.items():
            operand = operand.replace(name, str(value))
        return operand

    for name in '''
        push pop mov lea
        xor sub add
        '''.split():
        locals()['visit_' + name] = getattr(FunctionGcRootTracker,
                                            'visit_' + name + 'l')

    visit_int = FunctionGcRootTracker.visit_nop
    # probably not GC pointers
    visit_cdq  = FunctionGcRootTracker.visit_nop

    def visit_npad(self, line):
        # MASM has a nasty bug: it implements "npad 5" with "add eax, 0"
        # which is a not no-op because it clears flags.
        # I've seen this instruction appear between "test" and "jne"...
        # see http://www.masm32.com/board/index.php?topic=13122
        match = self.r_unaryinsn.match(line)
        arg = match.group(1)
        if arg == "5":
            # replace with "npad 3; npad 2"
            self.lines[self.currentlineno] = "\tnpad\t3\n" "\tnpad\t2\n"
        return []

    def extract_immediate(self, value):
        try:
            return int(value)
        except ValueError:
            return None

    def _visit_gcroot_marker(self, line=None):
        # two possible patterns:
        # 1. mov reg, DWORD PTR _always_one_
        #    imul target, reg
        # 2. mov reg, DWORD PTR _always_one_
        #    imul reg, target
        assert self.lines[self.currentlineno].startswith("\tmov\t")
        mov = self.r_binaryinsn.match(self.lines[self.currentlineno])
        assert re.match("DWORD PTR .+_always_one_", mov.group("source"))
        reg = mov.group("target")

        self.lines[self.currentlineno] = ";" + self.lines[self.currentlineno]

        # the 'imul' must appear in the same block; the 'reg' must not
        # appear in the instructions between
        imul = None
        lineno = self.currentlineno + 1
        stop = False
        while not stop:
            line = self.lines[lineno]
            if line == '\n':
                stop = True
            elif line.startswith("\tjmp\t"):
                stop = True
            elif self.r_gcroot_marker_var.search(line):
                stop = True
            elif (line.startswith("\tmov\t%s," % (reg,)) or
                  line.startswith("\tmovsx\t%s," % (reg,)) or
                  line.startswith("\tmovzx\t%s," % (reg,))):
                # mov reg, <arg>
                stop = True
            elif line.startswith("\txor\t%s, %s" % (reg, reg)):
                # xor reg, reg
                stop = True
            elif line.startswith("\timul\t"):
                imul = self.r_binaryinsn.match(line)
                imul_arg1 = imul.group("target")
                imul_arg2 = imul.group("source")
                if imul_arg1 == reg or imul_arg2 == reg:
                    break
            # the register may not appear in other instructions
            elif reg in line:
                assert False, (line, lineno)

            lineno += 1
        else:
            # No imul, the returned value is not used in this function
            return []

        if reg == imul_arg2:
            self.lines[lineno] = ";" + self.lines[lineno]
            return InsnGCROOT(self.replace_symbols(imul_arg1))
        else:
            assert reg == imul_arg1
            self.lines[lineno] = "\tmov\t%s, %s\n" % (imul_arg1, imul_arg2)
            if imul_arg2.startswith('OFFSET '):
                # ignore static global variables
                pass
            else:
                self.lines[lineno] += "\t; GCROOT\n"

            return []

    def insns_for_copy(self, source, target):
        if self.r_gcroot_marker_var.match(source):
            return self._visit_gcroot_marker()
        if self.lines[self.currentlineno].endswith("\t; GCROOT\n"):
            insns = [InsnGCROOT(self.replace_symbols(source))]
        else:
            insns = []
        return insns + super(MsvcFunctionGcRootTracker, self).insns_for_copy(source, target)


MsvcFunctionGcRootTracker.init_regexp()

class AssemblerParser(object):
    def __init__(self, verbose=0, shuffle=False):
        self.verbose = verbose
        self.shuffle = shuffle
        self.gcmaptable = []
        self.seen_main = False

    def process(self, iterlines, newfile, entrypoint='main', filename='?'):
        for in_function, lines in self.find_functions(iterlines):
            if in_function:
                tracker = self.process_function(lines, entrypoint, filename)
                lines = tracker.lines
            self.write_newfile(newfile, lines, filename.split('.')[0])
        if self.verbose == 1:
            sys.stderr.write('\n')

    def write_newfile(self, newfile, lines, grist):
        newfile.writelines(lines)

    def process_function(self, lines, entrypoint, filename):
        tracker = self.FunctionGcRootTracker(
            lines, filetag=getidentifier(filename))
        is_main = tracker.funcname == entrypoint
        tracker.is_stack_bottom = is_main
        if self.verbose == 1:
            sys.stderr.write('.')
        elif self.verbose > 1:
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
        self.seen_main |= is_main
        return tracker

class ElfAssemblerParser(AssemblerParser):
    format = "elf"
    FunctionGcRootTracker = ElfFunctionGcRootTracker

    def find_functions(self, iterlines):
        functionlines = []
        in_function = False
        for line in iterlines:
            if self.FunctionGcRootTracker.r_functionstart.match(line):
                assert not in_function, (
                    "missed the end of the previous function")
                yield False, functionlines
                in_function = True
                functionlines = []
            functionlines.append(line)
            if self.FunctionGcRootTracker.r_functionend.match(line):
                assert in_function, (
                    "missed the start of the current function")
                yield True, functionlines
                in_function = False
                functionlines = []
        assert not in_function, (
            "missed the end of the previous function")
        yield False, functionlines

class DarwinAssemblerParser(AssemblerParser):
    format = "darwin"
    FunctionGcRootTracker = DarwinFunctionGcRootTracker

    r_textstart = re.compile(r"\t.text\s*$")

    # see
    # http://developer.apple.com/documentation/developertools/Reference/Assembler/040-Assembler_Directives/asm_directives.html
    OTHERSECTIONS = ['section', 'zerofill',
                     'const', 'static_const', 'cstring',
                     'literal4', 'literal8', 'literal16',
                     'constructor', 'desctructor',
                     'symbol_stub',
                     'data', 'static_data',
                     'non_lazy_symbol_pointer', 'lazy_symbol_pointer',
                     'dyld', 'mod_init_func', 'mod_term_func',
                     'const_data'
                     ]
    r_sectionstart = re.compile(r"\t\.("+'|'.join(OTHERSECTIONS)+").*$")

    def find_functions(self, iterlines):
        functionlines = []
        in_text = False
        in_function = False
        for n, line in enumerate(iterlines):
            if self.r_textstart.match(line):
                assert not in_text, "unexpected repeated .text start: %d" % n
                in_text = True
            elif self.r_sectionstart.match(line):
                if in_function:
                    yield in_function, functionlines
                    functionlines = []
                in_text = False
                in_function = False
            elif in_text and self.FunctionGcRootTracker.r_functionstart.match(line):
                yield in_function, functionlines
                functionlines = []
                in_function = True
            functionlines.append(line)

        if functionlines:
            yield in_function, functionlines

    def process_function(self, lines, entrypoint, filename):
        entrypoint = '_' + entrypoint
        return super(DarwinAssemblerParser, self).process_function(
            lines, entrypoint, filename)

class Mingw32AssemblerParser(DarwinAssemblerParser):
    format = "mingw32"
    FunctionGcRootTracker = Mingw32FunctionGcRootTracker

    def find_functions(self, iterlines):
        functionlines = []
        in_text = False
        in_function = False
        for n, line in enumerate(iterlines):
            if self.r_textstart.match(line):
                in_text = True
            elif self.r_sectionstart.match(line):
                in_text = False
            elif in_text and self.FunctionGcRootTracker.r_functionstart.match(line):
                yield in_function, functionlines
                functionlines = []
                in_function = True
            functionlines.append(line)
        if functionlines:
            yield in_function, functionlines

class MsvcAssemblerParser(AssemblerParser):
    format = "msvc"
    FunctionGcRootTracker = MsvcFunctionGcRootTracker

    def find_functions(self, iterlines):
        functionlines = []
        in_function = False
        in_segment = False
        ignore_public = False
        self.inline_functions = {}
        for line in iterlines:
            if line.startswith('; File '):
                filename = line[:-1].split(' ', 2)[2]
                ignore_public = ('wspiapi.h' in filename.lower())
            if ignore_public:
                # this header define __inline functions, that are
                # still marked as PUBLIC in the generated assembler
                if line.startswith(';\tCOMDAT '):
                    funcname = line[:-1].split(' ', 1)[1]
                    self.inline_functions[funcname] = True
                elif line.startswith('PUBLIC\t'):
                    funcname = line[:-1].split('\t')[1]
                    self.inline_functions[funcname] = True

            if self.FunctionGcRootTracker.r_segmentstart.match(line):
                in_segment = True
            elif self.FunctionGcRootTracker.r_functionstart.match(line):
                assert not in_function, (
                    "missed the end of the previous function")
                in_function = True
                if in_segment:
                    yield False, functionlines
                    functionlines = []
            functionlines.append(line)
            if self.FunctionGcRootTracker.r_segmentend.match(line):
                yield False, functionlines
                in_segment = False
                functionlines = []
            elif self.FunctionGcRootTracker.r_functionend.match(line):
                assert in_function, (
                    "missed the start of the current function")
                yield True, functionlines
                in_function = False
                functionlines = []
        assert not in_function, (
            "missed the end of the previous function")
        yield False, functionlines

    def process_function(self, lines, entrypoint, filename):
        entrypoint = '_' + entrypoint
        return super(MsvcAssemblerParser, self).process_function(
            lines, entrypoint, filename)

    def write_newfile(self, newfile, lines, grist):
        newlines = []
        for line in lines:
            # truncate long comments
            if line.startswith(";"):
                line = line[:-1][:500] + '\n'

            # Workaround a bug in the .s files generated by msvc
            # compiler: every string or float constant is exported
            # with a name built after its value, and will conflict
            # with other modules.
            if line.startswith("PUBLIC\t"):
                symbol = line[:-1].split()[1]
                if symbol.startswith('__real@'):
                    line = '; ' + line
                elif symbol.startswith("__mask@@"):
                    line = '; ' + line
                elif symbol.startswith("??_C@"):
                    line = '; ' + line
                elif symbol == "__$ArrayPad$":
                    line = '; ' + line
                elif symbol in self.inline_functions:
                    line = '; ' + line

            # The msvc compiler writes "fucomip ST(1)" when the correct
            # syntax is "fucomip ST, ST(1)"
            if line == "\tfucomip\tST(1)\n":
                line = "\tfucomip\tST, ST(1)\n"

            # Because we insert labels in the code, some "SHORT" jumps
            # are now longer than 127 bytes.  We turn them all into
            # "NEAR" jumps.  Note that the assembler allocates space
            # for a near jump, but still generates a short jump when
            # it can.
            line = line.replace('\tjmp\tSHORT ', '\tjmp\t')
            line = line.replace('\tjne\tSHORT ', '\tjne\t')
            line = line.replace('\tje\tSHORT ',  '\tje\t')

            newlines.append(line)

            if line == "\t.model\tflat\n":
                newlines.append("\tassume fs:nothing\n")

        newfile.writelines(newlines)

PARSERS = {
    'elf': ElfAssemblerParser,
    'darwin': DarwinAssemblerParser,
    'mingw32': Mingw32AssemblerParser,
    'msvc': MsvcAssemblerParser,
    }

class GcRootTracker(object):

    def __init__(self, verbose=0, shuffle=False, format='elf'):
        self.verbose = verbose
        self.shuffle = shuffle     # to debug the sorting logic in asmgcroot.py
        self.format = format
        self.gcmaptable = []
        self.seen_main = False

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

        def _globalname(name, disp=""):
            if self.format in ('darwin', 'mingw32', 'msvc'):
                name = '_' + name
            return name

        def _variant(**kwargs):
            txt = kwargs[self.format]
            print >> output, "\t%s" % txt

        # The pypy_asm_stackwalk() function

        if self.format == 'msvc':
            print >> output, """\
            /* A circular doubly-linked list of all
             * the ASM_FRAMEDATAs currently alive
             */
            struct asm_framedata {
                struct asm_framedata* prev;
                struct asm_framedata* next;
            } __gcrootanchor = { &__gcrootanchor, &__gcrootanchor };

            /* See description in asmgcroot.py */
            __declspec(naked)
            long pypy_asm_stackwalk(void *callback)
            {
               __asm {
                mov\tedx, DWORD PTR [esp+4]\t; my argument, which is the callback
                mov\teax, esp\t\t; my frame top address
                push\teax\t\t\t; ASM_FRAMEDATA[6]
                push\tebp\t\t\t; ASM_FRAMEDATA[5]
                push\tedi\t\t\t; ASM_FRAMEDATA[4]
                push\tesi\t\t\t; ASM_FRAMEDATA[3]
                push\tebx\t\t\t; ASM_FRAMEDATA[2]

            ; Add this ASM_FRAMEDATA to the front of the circular linked
            ; list.  Let's call it 'self'.

                mov\teax, DWORD PTR [__gcrootanchor+4]\t\t; next = gcrootanchor->next
                push\teax\t\t\t\t\t\t\t\t\t; self->next = next
                push\tOFFSET __gcrootanchor              ; self->prev = gcrootanchor
                mov\tDWORD PTR [__gcrootanchor+4], esp\t\t; gcrootanchor->next = self
                mov\tDWORD PTR [eax+0], esp\t\t\t\t\t; next->prev = self

                call\tedx\t\t\t\t\t\t; invoke the callback

            ; Detach this ASM_FRAMEDATA from the circular linked list
                pop\tesi\t\t\t\t\t\t\t; prev = self->prev
                pop\tedi\t\t\t\t\t\t\t; next = self->next
                mov\tDWORD PTR [esi+4], edi\t\t; prev->next = next
                mov\tDWORD PTR [edi+0], esi\t\t; next->prev = prev

                pop\tebx\t\t\t\t; restore from ASM_FRAMEDATA[2]
                pop\tesi\t\t\t\t; restore from ASM_FRAMEDATA[3]
                pop\tedi\t\t\t\t; restore from ASM_FRAMEDATA[4]
                pop\tebp\t\t\t\t; restore from ASM_FRAMEDATA[5]
                pop\tecx\t\t\t\t; ignored      ASM_FRAMEDATA[6]
            ; the return value is the one of the 'call' above,
            ; because %eax (and possibly %edx) are unmodified
                ret
               }
            }
            """

        else:
            print >> output, "\t.text"
            print >> output, "\t.globl %s" % _globalname('pypy_asm_stackwalk')
            _variant(elf='.type pypy_asm_stackwalk, @function',
                     darwin='',
                     mingw32='')
            print >> output, "%s:" % _globalname('pypy_asm_stackwalk')

            print >> output, """\
            /* See description in asmgcroot.py */
            movl\t4(%esp), %edx\t/* my argument, which is the callback */
            movl\t%esp, %eax\t/* my frame top address */
            pushl\t%eax\t\t/* ASM_FRAMEDATA[6] */
            pushl\t%ebp\t\t/* ASM_FRAMEDATA[5] */
            pushl\t%edi\t\t/* ASM_FRAMEDATA[4] */
            pushl\t%esi\t\t/* ASM_FRAMEDATA[3] */
            pushl\t%ebx\t\t/* ASM_FRAMEDATA[2] */

            /* Add this ASM_FRAMEDATA to the front of the circular linked */
            /* list.  Let's call it 'self'.                               */

            movl\t__gcrootanchor + 4, %eax\t/* next = gcrootanchor->next */
            pushl\t%eax\t\t\t\t/* self->next = next */
            pushl\t$__gcrootanchor\t\t\t/* self->prev = gcrootanchor */
            movl\t%esp, __gcrootanchor + 4\t/* gcrootanchor->next = self */
            movl\t%esp, 0(%eax)\t\t\t/* next->prev = self */

            /* note: the Mac OS X 16 bytes aligment must be respected. */
            call\t*%edx\t\t/* invoke the callback */

            /* Detach this ASM_FRAMEDATA from the circular linked list */
            popl\t%esi\t\t/* prev = self->prev */
            popl\t%edi\t\t/* next = self->next */
            movl\t%edi, 4(%esi)\t/* prev->next = next */
            movl\t%esi, 0(%edi)\t/* next->prev = prev */

            popl\t%ebx\t\t/* restore from ASM_FRAMEDATA[2] */
            popl\t%esi\t\t/* restore from ASM_FRAMEDATA[3] */
            popl\t%edi\t\t/* restore from ASM_FRAMEDATA[4] */
            popl\t%ebp\t\t/* restore from ASM_FRAMEDATA[5] */
            popl\t%ecx\t\t/* ignored      ASM_FRAMEDATA[6] */

            /* the return value is the one of the 'call' above, */
            /* because %eax (and possibly %edx) are unmodified  */
            ret
            """.replace("__gcrootanchor", _globalname("__gcrootanchor"))

            _variant(elf='.size pypy_asm_stackwalk, .-pypy_asm_stackwalk',
                     darwin='',
                     mingw32='')

        if self.format == 'msvc':
            for label, state, is_range in self.gcmaptable:
                label = label[1:]
                print >> output, "extern void* %s;" % label
        else:
            print >> output, """\
            /* A circular doubly-linked list of all */
            /* the ASM_FRAMEDATAs currently alive */
            .data
            .align 4
            .globl __gcrootanchor
            __gcrootanchor:
            .long\t__gcrootanchor       /* prev */
            .long\t__gcrootanchor       /* next */
            """.replace("__gcrootanchor", _globalname("__gcrootanchor"))

        shapes = {}
        shapelines = []
        shapeofs = 0

        # write the tables

        if self.format == 'msvc':
            print >> output, """\
            static struct { void* addr; long shape; } __gcmap[%d] = {
            """ % (len(self.gcmaptable),)
            for label, state, is_range in self.gcmaptable:
                label = label[1:]
                try:
                    n = shapes[state]
                except KeyError:
                    n = shapes[state] = shapeofs
                    bytes = [str(b) for b in compress_callshape(state)]
                    shapelines.append('\t%s,\t/* %s */\n' % (
                            ', '.join(bytes),
                            shapeofs))
                    shapeofs += len(bytes)
                if is_range:
                    n = ~ n
                print >> output, '{ &%s, %d},' % (label, n)
            print >> output, """\
            };
            void* __gcmapstart = __gcmap;
            void* __gcmapend = __gcmap + %d;

            char __gccallshapes[] = {
            """ % (len(self.gcmaptable),)
            output.writelines(shapelines)
            print >> output, """\
            };
            """
        else:
            print >> output, """\
            .globl __gcmapstart
            __gcmapstart:
            """.replace("__gcmapstart", _globalname("__gcmapstart"))

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
                print >> output, '\t.long\t%s-%d' % (
                    label,
                    PARSERS[self.format].FunctionGcRootTracker.OFFSET_LABELS)
                print >> output, '\t.long\t%d' % (n,)

            print >> output, """\
            .globl __gcmapend
            __gcmapend:
            """.replace("__gcmapend", _globalname("__gcmapend"))

            _variant(elf='.section\t.rodata',
                     darwin='.const',
                     mingw32='')

            print >> output, """\
            .globl __gccallshapes
            __gccallshapes:
            """.replace("__gccallshapes", _globalname("__gccallshapes"))
            output.writelines(shapelines)

    def process(self, iterlines, newfile, entrypoint='main', filename='?'):
        parser = PARSERS[format](verbose=self.verbose, shuffle=self.shuffle)
        for in_function, lines in parser.find_functions(iterlines):
            if in_function:
                tracker = parser.process_function(lines, entrypoint, filename)
                lines = tracker.lines
            parser.write_newfile(newfile, lines, filename.split('.')[0])
        if self.verbose == 1:
            sys.stderr.write('\n')
        if self.shuffle and random.random() < 0.5:
            self.gcmaptable[:0] = parser.gcmaptable
        else:
            self.gcmaptable.extend(parser.gcmaptable)
        self.seen_main |= parser.seen_main


class UnrecognizedOperation(Exception):
    pass

class NoPatternMatch(Exception):
    pass


# __________ debugging output __________

def format_location(loc):
    # A 'location' is a single number describing where a value is stored
    # across a call.  It can be in one of the CALLEE_SAVE_REGISTERS, or
    # in the stack frame at an address relative to either %esp or %ebp.
    # The last two bits of the location number are used to tell the cases
    # apart; see format_location().
    assert loc >= 0
    kind = loc & LOC_MASK
    if kind == LOC_REG:
        if loc == LOC_NOWHERE:
            return '?'
        reg = (loc >> 2) - 1
        return ElfFunctionGcRootTracker.CALLEE_SAVE_REGISTERS[reg]
    else:
        offset = loc & ~ LOC_MASK
        if kind == LOC_EBP_PLUS:
            result = '(%ebp)'
        elif kind == LOC_EBP_MINUS:
            result = '(%ebp)'
            offset = -offset
        elif kind == LOC_ESP_PLUS:
            result = '(%esp)'
        else:
            assert 0, kind
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
        assert loc >= 0
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
        result.append(value)
    result.reverse()
    assert result[5] == 0
    del result[5]
    return result

def getidentifier(s):
    def mapchar(c):
        if c.isalnum():
            return c
        else:
            return '_'
    if s.endswith('.s'):
        s = s[:-2]
    s = ''.join([mapchar(c) for c in s])
    while s.endswith('__'):
        s = s[:-1]
    return s


if __name__ == '__main__':
    verbose = 1
    shuffle = False
    output_raw_table = False
    if sys.platform == 'darwin':
        format = 'darwin'
    elif sys.platform == 'win32':
        format = 'mingw32'
    else:
        format = 'elf'
    entrypoint = 'main'
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
        elif sys.argv[1].startswith('-f'):
            format = sys.argv[1][2:]
            del sys.argv[1]
        elif sys.argv[1].startswith('-m'):
            entrypoint = sys.argv[1][2:]
            del sys.argv[1]
        else:
            break
    tracker = GcRootTracker(verbose=verbose, shuffle=shuffle, format=format)
    for fn in sys.argv[1:]:
        f = open(fn, 'r')
        firstline = f.readline()
        f.seek(0)
        assert firstline, "file %r is empty!" % (fn,)
        if firstline.startswith('seen_main = '):
            tracker.reload_raw_table(f)
            f.close()
        else:
            assert fn.endswith('.s'), fn
            lblfn = fn[:-2] + '.lbl.s'
            g = open(lblfn, 'w')
            try:
                tracker.process(f, g, entrypoint=entrypoint, filename=fn)
            except:
                g.close()
                os.unlink(lblfn)
                raise
            g.close()
            f.close()
            if output_raw_table:
                tracker.dump_raw_table(sys.stdout)
    if not output_raw_table:
        tracker.dump(sys.stdout)
