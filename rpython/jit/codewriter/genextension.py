import py
import re
from rpython.jit.metainterp.history import (Const, ConstInt, ConstPtr,
    ConstFloat, CONST_NULL)
from rpython.flowspace.model import Constant

class GenExtension(object):
    def __init__(self, assembler):
        self.assembler = assembler
        self.insns = [None] * len(assembler.insns)
        for insn, index in assembler.insns.iteritems():
            self.insns[index] = insn

    def setup(self, ssarepr, jitcode):
        self.ssarepr = ssarepr
        self.jitcode = jitcode
        self.precode = []
        self.pc_to_insn = {}
        self.pc_to_nextpc = {}
        self.code = []
        self.globals = {}
        self._reset_insn()

    def _reset_insn(self):
        # the following attributes are set for each instruction emitted
        self.name = None
        self.methodname = None
        self.argcodes = None
        self.insn = None
        self.args = None
        self.args_as_objects = None
        self.returncode = None
        self.returnindex = None

    def generate(self, ssarepr, jitcode):
        from rpython.jit.codewriter.flatten import Label
        from rpython.jit.codewriter.jitcode import JitCode
        from rpython.jit.metainterp.pyjitpl import ChangeFrame
        self.setup(ssarepr, jitcode)
        self.precode.append("def jit_shortcut(self): # %s" % jitcode.name)
        self.precode.append("    pc = self.pc")
        self.precode.append("    while 1:")
        for index, insn in enumerate(ssarepr.insns):
            self._reset_insn()
            if isinstance(insn[0], Label) or insn[0] == '---':
                continue
            pc = ssarepr._insns_pos[index]
            self.pc_to_insn[pc] = insn
            if index == len(self.ssarepr.insns) - 1:
                nextpc = len(self.jitcode.code)
            else:
                nextpc = self.ssarepr._insns_pos[index + 1]
            self.pc_to_nextpc[pc] = nextpc

        for index, insn in enumerate(ssarepr.insns):
            self._reset_insn()
            if isinstance(insn[0], Label) or insn[0] == '---':
                continue
            self.insn = insn
            pc = ssarepr._insns_pos[index]
            self.code.append("if pc == %s: # %s" % (pc, self.insn))
            nextpc = self.pc_to_nextpc[pc]
            self.code.append("    self.pc = %s" % (nextpc, ))
            instruction = self.insns[ord(self.jitcode.code[pc])]
            self.name, self.argcodes = instruction.split("/")
            self.methodname = 'opimpl_' + self.name
            lines, needed_orgpc, needed_label = self._parse_args(index, pc, nextpc)
            for line in lines:
                self.code.append("    " + line)
            meth = getattr(self, "emit_" + self.name, self.emit_default)
            lines = meth()
            for line in lines:
                self.code.append("    " + line)
            pcs = self.next_possible_pcs(insn, needed_label, nextpc)
            if len(pcs) == 0:
                self.code.append("    assert 0 # unreachable")
                continue
            elif len(pcs) == 1:
                next_insn = self.pc_to_insn[pcs[0]]
                goto_target = self._find_actual_jump_target_chain(next_insn, pcs[0])
                self.code.append("    pc = %s" % goto_target)
            else:
                self.code.append("    pc = self.pc")
                # do the trick
                prefix = ''
                for pc in pcs:
                    next_insn = self.pc_to_insn[pc]
                    goto_target = self._find_actual_jump_target(next_insn, pc)
                    self.code.append("    %sif pc == %s: pc = %s" % (prefix, pc, goto_target))
                    prefix = "el"
                self.code.append("    else:")
                self.code.append("        assert 0 # unreachable")
            self.code.append("    continue")
        self.code.append("assert 0 # unreachable")
        allcode = []
        allcode.extend(self.precode)
        for line in self.code:
            allcode.append(" " * 8 + line)
        jitcode._genext_source = "\n".join(allcode)
        d = {"ConstInt": ConstInt, "JitCode": JitCode, "ChangeFrame": ChangeFrame}
        d.update(self.globals)
        source = py.code.Source(jitcode._genext_source)
        exec source.compile() in d
        print jitcode._genext_source
        jitcode.genext_function = d['jit_shortcut']
        jitcode.genext_function.__name__ += "_" + jitcode.name

    def _add_global(self, obj):
        name = "glob%s" % len(self.globals)
        self.globals[name] = obj
        return name

    def _decode_label(self, position):
        code = self.jitcode.code
        needed_label = ord(code[position]) | (ord(code[position+1])<<8)
        return needed_label

    def _find_actual_jump_target(self, next_insn, targetpc):
        if next_insn[0] == 'goto':
            return self._decode_label(targetpc+1)
        elif next_insn[0] == '-live-':
            return self.pc_to_nextpc[targetpc]
        else:
            # otherwise, just return pc
            return targetpc

    def _find_actual_jump_target_chain(self, next_insn, targetpc):
        insn = next_insn[0]
        while True:
            if insn == 'goto':
                targetpc = self._decode_label(targetpc+1)
            elif insn == '-live-':
                targetpc = self.pc_to_nextpc[targetpc]
            else:
                break
            insn = self.pc_to_insn[targetpc][0]
        return targetpc

    def _parse_args(self, index, pc, nextpc):
        from rpython.jit.metainterp.pyjitpl import MIFrame
        from rpython.jit.metainterp.blackhole import signedord
        lines = []

        unboundmethod = getattr(MIFrame, self.methodname).im_func
        argtypes = unboundmethod.argtypes

        # collect arguments, this is a 'timeshifted' version of the code in
        # pyjitpl._get_opimpl_method
        args = []
        args_as_objects = []
        next_argcode = 0
        code = self.jitcode.code
        orgpc = pc
        position = pc
        position += 1
        needed_orgpc = False
        needed_label = None
        for argtype in argtypes:
            arg_as_object = None
            if argtype == "box":     # a box, of whatever type
                argcode = self.argcodes[next_argcode]
                next_argcode = next_argcode + 1
                if argcode == 'i':
                    value = "self.registers_i[%s]" % (ord(code[position]), )
                elif argcode == 'c':
                    value = "ConstInt(%s)" % signedord(code[position])
                elif argcode == 'r':
                    value = "self.registers_r[%s]" % (ord(code[position]), )
                elif argcode == 'f':
                    value = "self.registers_f[%s]" % (ord(code[position]), )
                else:
                    raise AssertionError("bad argcode")
                position += 1
            elif argtype == "descr" or argtype == "jitcode":
                assert self.argcodes[next_argcode] == 'd'
                next_argcode = next_argcode + 1
                index = ord(code[position]) | (ord(code[position+1])<<8)
                arg_as_object = self.assembler.descrs[index]
                value = self._add_global(arg_as_object)
                if argtype == "jitcode":
                    self.code.append("    assert isinstance(%s, JitCode)" % value)
                position += 2
            elif argtype == "label":
                assert self.argcodes[next_argcode] == 'L'
                next_argcode = next_argcode + 1
                assert needed_label is None # only one label per instruction
                needed_label = self._decode_label(position)
                value = str(needed_label)
                position += 2
            elif argtype == "boxes":     # a list of boxes of some type
                length = ord(code[position])
                value = [None] * length
                self.prepare_list_of_boxes(value, 0, position,
                                           self.argcodes[next_argcode])
                next_argcode = next_argcode + 1
                position += 1 + length
                value = '[' + ",".join(value) + "]"
            elif argtype == "boxes2":     # two lists of boxes merged into one
                length1 = ord(code[position])
                position2 = position + 1 + length1
                length2 = ord(code[position2])
                value = [None] * (length1 + length2)
                self.prepare_list_of_boxes(value, 0, position,
                                           self.argcodes[next_argcode])
                self.prepare_list_of_boxes(value, length1, position2,
                                           self.argcodes[next_argcode + 1])
                next_argcode = next_argcode + 2
                position = position2 + 1 + length2
                value = '[' + ",".join(value) + "]"
            elif argtype == "boxes3":    # three lists of boxes merged into one
                length1 = ord(code[position])
                position2 = position + 1 + length1
                length2 = ord(code[position2])
                position3 = position2 + 1 + length2
                length3 = ord(code[position3])
                value = [None] * (length1 + length2 + length3)
                self.prepare_list_of_boxes(value, 0, position,
                                           self.argcodes[next_argcode])
                self.prepare_list_of_boxes(value, length1, position2,
                                           self.argcodes[next_argcode + 1])
                self.prepare_list_of_boxes(value, length1 + length2, position3,
                                           self.argcodes[next_argcode + 2])
                next_argcode = next_argcode + 3
                position = position3 + 1 + length3
                value = '[' + ",".join(value) + "]"
            elif argtype == "newframe" or argtype == "newframe2" or argtype == "newframe3":
                assert argtypes == (argtype, )
                # this and the next two are basically equivalent to
                # jitcode boxes/boxes2/boxes3
                # instead of allocating the list of boxes, just put everything
                # into the correct position of a new MIFrame

                # first get the jitcode
                assert self.argcodes[next_argcode] == 'd'
                next_argcode = next_argcode + 1
                index = ord(code[position]) | (ord(code[position+1])<<8)
                value = argname = "arg%s" % position
                jitcode = self._add_global(self.assembler.descrs[index])
                lines.append("assert isinstance(%s, JitCode)" % jitcode)
                position += 2
                # make a new frame
                lines.append("%s = self.metainterp.newframe(%s)" % (argname, jitcode))
                lines.append("%s.pc = 0" % (argname, ))

                # generate code to put boxes into the right places
                length = ord(code[position])
                self.fill_registers(lines, argname, length, position + 1,
                                    self.argcodes[next_argcode])
                next_argcode = next_argcode + 1
                position += 1 + length
                if argtype != "newframe": # 2/3 lists of boxes
                    length = ord(code[position])
                    self.fill_registers(lines, argname, length, position + 1,
                                        self.argcodes[next_argcode])
                    next_argcode = next_argcode + 1
                    position += 1 + length
                if argtype == "newframe3": # 3 lists of boxes
                    length = ord(code[position])
                    self.fill_registers(lines, argname, length, position + 1,
                                        self.argcodes[next_argcode])
                    next_argcode = next_argcode + 1
                    position += 1 + length
            elif argtype == "orgpc":
                value = str(orgpc)
                needed_orgpc = True
            elif argtype == "int":
                argcode = self.argcodes[next_argcode]
                next_argcode = next_argcode + 1
                if argcode == 'i':
                    pos = ord(code[position])
                    num_regs_i = self.jitcode.num_regs_i()
                    value = "self.registers_i[%s].getint()" % (pos, )
                    if pos >= num_regs_i:
                        intval = self.jitcode.constants_i[pos - num_regs_i]
                        if isinstance(intval, int):
                            value = str(intval)
                elif argcode == 'c':
                    value = str(signedord(code[position]))
                else:
                    raise AssertionError("bad argcode")
                position += 1
            elif argtype == "jitcode_position":
                value = str(position)
            else:
                raise AssertionError("bad argtype: %r" % (argtype,))
            args.append(value)
            args_as_objects.append(arg_as_object)
        num_return_args = len(self.argcodes) - next_argcode
        assert num_return_args == 0 or num_return_args == 2
        if num_return_args:
            returncode = self.argcodes[next_argcode + 1]
            resindex = ord(code[position])
        else:
            returncode = 'v'
            resindex = -1
        self.args = args
        self.args_as_objects = args_as_objects
        self.returncode = returncode
        self.resindex = resindex
        return lines, needed_orgpc, needed_label

    def emit_live(self):
        return ["pass # live"]

    def emit_goto(self):
        assert len(self.args) == 1
        lines = []
        targetpc = int(self.args[0])
        next_insn = self.pc_to_insn[targetpc]
        goto_target = self._find_actual_jump_target_chain(next_insn, targetpc)
        lines.append("pc = self.pc = %s # goto" % (goto_target, ))
        lines.append("continue")
        return lines

    def emit_switch(self):
        lines = []
        arg, descr, pc = self.args_as_objects
        argvalue, argname, pc = self.args
        lines.append("arg = %s" % (argvalue))
        lines.append("if arg.is_constant():")
        lines.append("    value = arg.getint()")
        dict_switch = descr.as_dict()
        prefix = ''
        for pc in dict_switch:
            targetpc = dict_switch[pc]
            next_insn = self.pc_to_insn[targetpc]
            targetpc = self._find_actual_jump_target(next_insn, targetpc)
            lines.append("    %sif value == %d:" % (prefix, pc))
            lines.append("        pc = self.pc = %d" % targetpc)
            lines.append("        continue")
            prefix = 'el'
        lines.append("    else:")
        lines.append("        assert 0 # unreachable")
        newlines = self.emit_default()
        return lines + newlines

    def emit_newframe_function(self):
        return ["self._result_argcode = %r" % (self.returncode, ), "return # change frame"]
    emit_inline_call_r_i = emit_newframe_function
    emit_inline_call_r_r = emit_newframe_function
    emit_inline_call_r_v = emit_newframe_function
    emit_inline_call_ir_i = emit_newframe_function
    emit_inline_call_ir_r = emit_newframe_function
    emit_inline_call_ir_v = emit_newframe_function
    emit_inline_call_irf_i = emit_newframe_function
    emit_inline_call_irf_r = emit_newframe_function
    emit_inline_call_irf_f = emit_newframe_function
    emit_inline_call_irf_v = emit_newframe_function

    def emit_default(self):
        lines = []
        strargs = ", ".join(self.args)
        if self.returncode != 'v':
            # Save the type of the resulting box.  This is needed if there is
            # a get_list_of_active_boxes().  See comments there.
            lines.append("self._result_argcode = %r" % (self.returncode, ))
            if self.returncode == "i":
                prefix = "self.registers_i[%s] = " % self.resindex
            elif self.returncode == "r":
                prefix = "self.registers_r[%s] = " % self.resindex
            elif self.returncode == "f":
                prefix = "self.registers_f[%s] = " % self.resindex
            else:
                assert 0
        else:
            lines.append("self._result_argcode = 'v'")
            prefix = ''

        lines.append("%sself.%s(%s)" % (prefix, self.methodname, strargs))
        return lines

    def emit_return(self):
        lines = []
        lines.append("try:")
        lines.append("    self.%s(%s)" % (self.methodname, self.args[0]))
        lines.append("except ChangeFrame: return")
        return lines

    emit_int_return = emit_return
    emit_ref_return = emit_return
    emit_float_return = emit_return

    def prepare_list_of_boxes(self, outvalue, startindex, position, argcode):
        assert argcode in 'IRF'
        code = self.jitcode.code
        length = ord(code[position])
        position += 1
        for i in range(length):
            index = ord(code[position+i])
            if   argcode == 'I': reg = "self.registers_i[%s]" % index
            elif argcode == 'R': reg = "self.registers_r[%s]" % index
            elif argcode == 'F': reg = "self.registers_f[%s]" % index
            else: raise AssertionError(argcode)
            outvalue[startindex+i] = reg

    def fill_registers(self, lines, argname, length, position, argcode):
        assert argcode in 'IRF'
        code = self.jitcode.code
        for i in range(length):
            index = ord(code[position+i])
            if   argcode == 'I':
                lines.append("%s.registers_i[%s] = self.registers_i[%s]" % (argname, i, index))
            elif argcode == 'R':
                lines.append("%s.registers_r[%s] = self.registers_r[%s]" % (argname, i, index))
            elif argcode == 'F':
                lines.append("%s.registers_f[%s] = self.registers_f[%s]" % (argname, i, index))
            else:
                raise AssertionError(argcode)

    def next_possible_pcs(self, insn, needed_label, nextpc):
        if insn[0] == "goto":
            return [needed_label]
        if needed_label is not None:
            return [nextpc, needed_label]
        if insn[0].endswith("return"):
            return []
        if insn[0].endswith("raise"):
            return []
        if insn[0] == "switch":
            return insn[2].dict.values() + [nextpc]
        else:
            return [nextpc]


class WorkList(object):
    def __init__(self):
        self.specialize_instruction = dict() # (pc, insn, constant?registers) =? Specializer
        self.todo = []
        self.free_pc = 100 # TODO: will be fixed as a dynamic number

    def specialize(self, insn, constant_registers, orig_pc):
        key = (orig_pc, insn, frozenset(constant_registers))
        if key in self.specialize_instruction:
            return self.specialize_instruction[key]
        else:
            if not constant_registers:
                spec_pc = orig_pc
            else:
                spec_pc = self.free_pc
                self.free_pc += 1
            spec = self.specialize_instruction[key] = Specializer(
                insn, constant_registers, orig_pc, spec_pc, self)
            self.todo.append(spec)
            return spec

class Specializer(object):
    def __init__(self, insn, constant_registers, orig_pc, spec_pc, work_list):
        self.insn = insn
        self.constant_registers = constant_registers
        self.orig_pc = orig_pc
        self.spec_pc = spec_pc
        if not constant_registers: # not specialized
            assert orig_pc == spec_pc
        self.work_list = work_list

        #assert self.insn[0] == 'int_add'

        self.name = self.insn[0]
        self.methodname = "opimpl_" + self.name
        self.resindex = len(self.insn) - 1 if '->' in self.insn else None

    def _reset_specializer(self):
        self.name = None
        self.methoname = None
        self.resindex = None

    def _get_args(self):
        if self.resindex:
            return self.insn[1:-2]
        else:
            return self.insn[1:]

    def get_pc(self):
        return self.spec_pc

    def is_constant(self, arg):
        return arg in self.constant_registers

    def make_code(self):
        args = self._get_args()
        if not self._check_all_constant_args(args):
            return self._make_code_unspecialized()
        return self._make_code_specialized()

    def _check_all_constant_args(self, args):
        for arg in args:
            if arg not in self.constant_registers and not isinstance(arg, Constant):
                return False
        return True

    def _make_code_specialized(self):
        meth = getattr(self, "emit_specialized_" + self.name)
        return '\n'.join(meth())

    def _make_code_unspecialized(self):
        meth = getattr(self, "emit_unspecialized_" + self.name)
        return '\n'.join(meth())

    def get_next_constant_registers(self):
        if not self.resindex:
            return self.constant_registers

        args = self._get_args()
        if not self._check_all_constant_args(args):
            return self.constant_registers - {self.insn[self.resindex]}
        return self.constant_registers.union({self.insn[self.resindex]})

    def emit_specialized_int_add(self):
        return self._emit_specialized_int_binary("+")

    def emit_specialized_int_sub(self):
        return self._emit_specialized_int_binary("-")

    def _emit_specialized_int_binary(self, op):
        args = self._get_args()
        if len(args) == 2:
            arg0, arg1 = args[0], args[1]
            result = self.insn[self.resindex]
            return ["i%s = %s %s %s" % (result.index, self._get_as_constant(arg0),
                                        op, self._get_as_constant(arg1))]
        else:
            assert False # TODO: add another cases

    def emit_specialized_strgetitem(self):
        args = self._get_args()
        if len(args) == 2:
            arg0, arg1 = args[0], args[1]
            # TODO: save result?!
            #result = self.insn[self.resindex]
            return ["ord(lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), r%d).chars[%s])" % (
                arg0.index, self._get_as_constant(arg1))]
        else:
            assert False # TODO: Here too?

    def _get_type_prefix(self, non_const_arg):
        #t = ('%s' % arg)[1]  # TODO: better way?
        t = re.search('%([i,r,f])[0-9]+', str(non_const_arg)).group(1)
        assert t is not None, "ensure regex match"
        return t

    def _get_as_constant(self, arg):
        if isinstance(arg, Constant):
            return str(arg.value)
        else:
            t = self._get_type_prefix(arg)
            return "%s%s" % (t, arg.index)

    def _get_as_box(self, arg):
        if isinstance(arg, Constant):
            return "ConstInt(%d)" % (arg.value)
        else:
            t = self._get_type_prefix(arg)
            return "r%s%d" % (t, arg.index)

    def emit_unspecialized_int_add(self):
        lines = []
        arg0, arg1 = self.insn[1], self.insn[2]
        result = self.insn[4]  # TODO: use self.resindex
        lines.append("ri%d = self.registers_i[%d]" % (arg0.index, arg0.index))
        if isinstance(arg1, Constant):
            lines.append("if ri%d.is_constant():" % (arg0.index))
            lines.append("    i%d = ri%d.getint()" % (arg0.index, arg0.index))
            next_constant_registers = {arg0}
        else:
            lines.append("ri%d = self.registers_i[%d]" % (arg1.index, arg1.index))
            lines.append("if ri%d.is_constant() and ri%d.is_constant():" % (arg0.index, arg1.index))
            lines.append("    i%d = ri%d.getint()" % (arg0.index, arg0.index))
            lines.append("    i%d = ri%d.getint()" % (arg1.index, arg1.index))
            next_constant_registers = {arg0, arg1}
        specializer = self.work_list.specialize(
            self.insn, self.constant_registers.union(next_constant_registers), self.orig_pc)
        lines.append("    pc = %d" % (specializer.get_pc()))
        lines.append("    continue")
        lines.append("else:")
        lines.append("    self.registers_i[%d] = self.%s(%s, %s)" % (
            result.index, self.methodname, self._get_as_box(arg0), self._get_as_box(arg1)))
        return lines
    emit_unspecialized_int_sub = emit_unspecialized_int_add

    def emit_unspecialized_strgetitem(self):
        lines = []
        arg0, arg1 = self.insn[1], self.insn[2]
        result = self.insn[4]
        lines.append("rr%d = self.registers_r[%d]" % (arg0.index, arg0.index))

        if isinstance(arg1, Constant):
            lines.append("if rr%d.is_constant():" % (arg0.index))
            lines.append("    i%d = ri%d.getint()" % (arg1.index, arg1.index))
            next_constant_registers = {arg0}
        else:
            lines.append("ri%d = self.registers_i[%d]" % (arg1.index, arg1.index))
            lines.append("if rr%d.is_constant() and ri%d.is_constant():" % (arg0.index, arg1.index))
            lines.append("    r%d = rr%d.getref_base()" % (arg0.index, arg0.index))
            lines.append("    i%d = ri%d.getint()" % (arg1.index, arg1.index))
            next_constant_registers = {arg0, arg1}
        specializer = self.work_list.specialize(
            self.insn, self.constant_registers.union(next_constant_registers), self.orig_pc)
        lines.append("    pc = %d" % (specializer.get_pc()))
        lines.append("    continue")
        lines.append("else:")
        import pdb; pdb.set_trace()
        lines.append("    self.registers_i[%d] = self.opimpl_strgetitem(%s, %s)" % (
            result.index, self._get_as_box(arg0), self._get_as_box(arg1)))
        return lines

