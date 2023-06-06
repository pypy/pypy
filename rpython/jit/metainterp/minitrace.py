from rpython.jit.codewriter.jitcode import JitCode, SwitchDictDescr
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp import history, jitexc, resume
from rpython.jit.metainterp.history import History
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import we_are_translated, specialize, always_inline
from rpython.jit.codewriter.liveness import OFFSET_SIZE
from rpython.jit.metainterp.valueapi import TYPE_FLOAT, TYPE_INT, TYPE_REF, valueapi
from rpython.rtyper.lltypesystem import lltype, rstr


def arguments(*args):
    def decorate(func):
        func = always_inline(func)
        func.argtypes = args
        return func
    return decorate

CONTINUE_EXECUTE = 0
CHANGE_FRAME = 1
DONE_WITH_FRAME_INT = 2

class MIFrame(object):
    debug = True

    def __init__(self, metainterp, jitcode):
        self.metainterp = metainterp
        self.jitcode = jitcode
        self.bytecode = jitcode.code

        # allocate registers
        self.registers_offset_i = self.metainterp.alloc_regs(jitcode.num_regs_i())
        self.registers_offset_r = self.metainterp.alloc_regs(jitcode.num_regs_r())
        self.registers_offset_f = self.metainterp.alloc_regs(jitcode.num_regs_f())
        
        self.parent_snapshot = None

    def get_reg_i(self, index):
        return self.metainterp.regs[self.registers_offset_i + index]
    
    def get_reg_r(self, index):
        return self.metainterp.regs[self.registers_offset_r + index]
    
    def get_reg_f(self, index):
        return self.metainterp.regs[self.registers_offset_f + index]
    
    def set_reg_i(self, index, value):
        self.metainterp.regs[self.registers_offset_i + index] = value
    
    def set_reg_r(self, index, value):
        self.metainterp.regs[self.registers_offset_r + index] = value
    
    def set_reg_f(self, index, value):
        self.metainterp.regs[self.registers_offset_f+ index] = value

    def setup_call(self, argboxes):
        self.pc = 0
        count_i = count_r = count_f = 0
        for box in argboxes:
            if valueapi.get_type(box) == TYPE_INT:
                self.set_reg_i(count_i, box)
                count_i += 1
            elif valueapi.get_type(box) == TYPE_REF:
                self.set_reg_r(count_r, box)
                count_r += 1
            elif valueapi.get_type(box) == TYPE_FLOAT:
                self.set_reg_f(count_f, box)
                count_f += 1
            else:
                raise AssertionError("unknown type")

    @always_inline
    def run_one_step(self):
        # Execute the frame forward.  This method contains a loop that leaves
        # whenever the 'opcode_implementations' (which is one of the 'opimpl_'
        # methods) raises ChangeFrame.  This is the case when the current frame
        # changes, due to a call or a return.
            staticdata = self.metainterp.metainterp_sd
            return staticdata.run_one_step(self)

    def generate_guard(self, opnum, box=None, extraarg=None, resumepc=-1):
        if valueapi.is_constant(box):    # no need for a guard
            return
        guard_op = self.metainterp.history.record1(opnum, box, None) # TODO
        
        saved_pc = 0
        if self.metainterp.framestack:
            frame = self.metainterp.framestack[-1]
            saved_pc = frame.pc
            if resumepc >= 0:
                frame.pc = resumepc
        resume.capture_resumedata(self.metainterp.framestack, None,
                                  [], self.metainterp.history.trace,
                                  False)
        if self.metainterp.framestack:
            self.metainterp.framestack[-1].pc = saved_pc
        
    def get_list_of_active_boxes(self, in_a_call, new_array, encode, after_residual_call=False):
        from rpython.jit.codewriter.liveness import decode_offset
        from rpython.jit.codewriter.liveness import LivenessIterator
        if in_a_call:
            # If we are not the topmost frame, self._result_argcode contains
            # the type of the result of the call instruction in the bytecode.
            # We use it to clear the box that will hold the result: this box
            # is not defined yet.
            argcode = self._result_argcode
            index = ord(self.bytecode[self.pc - 1])
            if argcode == 'i':
                self.set_reg_i(index, valueapi.CONST_FALSE)
            elif argcode == 'r':
                self.set_reg_r(index, valueapi.CONST_NULL)
            elif argcode == 'f':
                self.set_reg_f(index, valueapi.CONST_FZERO)
            self._result_argcode = '?'     # done
        if in_a_call or after_residual_call:
            pc = self.pc # live instruction afterwards
        else:
            # there needs to be a live instruction before
            SIZE_LIVE_OP = OFFSET_SIZE + 1
            pc = self.pc - SIZE_LIVE_OP
        assert ord(self.jitcode.code[pc]) == self.metainterp.metainterp_sd.op_live
        if not we_are_translated():
            assert pc in self.jitcode._startpoints
        offset = decode_offset(self.jitcode.code, pc + 1)
        all_liveness = self.metainterp.metainterp_sd.liveness_info
        length_i = ord(all_liveness[offset])
        length_r = ord(all_liveness[offset + 1])
        length_f = ord(all_liveness[offset + 2])
        offset += 3

        start_i = 0
        start_r = start_i + length_i
        start_f = start_r + length_r
        total   = start_f + length_f
        # allocate a list of the correct size
        env = new_array(total)
        # fill it now
        if length_i:
            it = LivenessIterator(offset, length_i, all_liveness)
            for index in it:
                env[start_i] = encode(self.get_reg_i(index))
                start_i += 1
            offset = it.offset
        if length_r:
            it = LivenessIterator(offset, length_r, all_liveness)
            for index in it:
                env[start_r] = encode(self.get_reg_r(index))
                start_r += 1
            offset = it.offset
        if length_f:
            it = LivenessIterator(offset, length_f, all_liveness)
            for index in it:
                env[start_f] = encode(self.get_reg_f(index))
                start_f += 1
            offset = it.offset
        return env

    @arguments("box", "box")
    def opimpl_int_add(self, b1, b2):
        res = valueapi.get_value_int(b1) + valueapi.get_value_int(b2)
        if not (valueapi.is_constant(b1) and valueapi.is_constant(b2)):
            res_box = self.metainterp.history.record2(rop.INT_ADD, b1, b2, res)
        else:
            res_box = valueapi.create_const(res)
        return res_box, CONTINUE_EXECUTE, valueapi.NoValue

    @arguments("box", "box")
    def opimpl_int_sub(self, b1, b2):
        res = valueapi.get_value_int(b1) - valueapi.get_value_int(b2)
        if not (valueapi.is_constant(b1) and valueapi.is_constant(b2)):
            res_box = self.metainterp.history.record2(rop.INT_SUB, b1, b2, res)
        else:
            res_box = valueapi.create_const(res)
        return res_box, CONTINUE_EXECUTE, valueapi.NoValue

    @arguments("box", "box")
    def opimpl_int_mul(self, b1, b2):
        res = valueapi.get_value_int(b1) * valueapi.get_value_int(b2)
        if not (valueapi.is_constant(b1) and valueapi.is_constant(b2)):
            res_box = self.metainterp.history.record2(rop.INT_MUL, b1, b2, res)
        else:
            res_box = valueapi.create_const(res)
        return res_box, CONTINUE_EXECUTE, valueapi.NoValue

    @arguments("box")
    def opimpl_int_copy(self, box):
        return box, CONTINUE_EXECUTE, valueapi.NoValue

    @arguments()
    def opimpl_live(self):
        self.pc += OFFSET_SIZE
        return None, CONTINUE_EXECUTE, valueapi.NoValue

    @arguments("box", "box", "label", "orgpc")
    def opimpl_goto_if_not_int_gt(self, a, b, target, orgpc):
        res = valueapi.get_value_int(a) > valueapi.get_value_int(b)
        if not (valueapi.is_constant(a) and valueapi.is_constant(b)):
            res_box = self.metainterp.history.record2(rop.INT_GT, a, b, res)
            if res:
                opnum = rop.GUARD_TRUE
            else:
                opnum = rop.GUARD_FALSE
            self.generate_guard(opnum, res_box, resumepc=orgpc)
        if not res:
            self.pc = target
        return None, CONTINUE_EXECUTE, valueapi.NoValue

    @arguments("box", "box", "label", "orgpc")
    def opimpl_goto_if_not_int_lt(self, a, b, target, orgpc):
        res = valueapi.get_value_int(a) < valueapi.get_value_int(b)
        if not (valueapi.is_constant(a) and valueapi.is_constant(b)):
            res_box = self.metainterp.history.record2(rop.INT_LT, a, b, res)
            if res:
                opnum = rop.GUARD_TRUE
            else:
                opnum = rop.GUARD_FALSE
            self.generate_guard(opnum, res_box, resumepc=orgpc)
        if not res:
            self.pc = target
        return None, CONTINUE_EXECUTE, valueapi.NoValue

    @arguments("box", "box", "label", "orgpc")
    def opimpl_goto_if_not_int_eq(self, a, b, target, orgpc):
        value_a, constness_a = valueapi.get_value_int_and_constness(a)
        value_b, constness_b = valueapi.get_value_int_and_constness(b)

        res = value_a == value_b
        if not (constness_a and constness_b):
            res_box = self.metainterp.history.record2(rop.INT_EQ, a, b, res)
            if res:
                opnum = rop.GUARD_TRUE
            else:
                opnum = rop.GUARD_FALSE
            self.generate_guard(opnum, res_box, resumepc=orgpc)
        if not res:
            self.pc = target
        return None, CONTINUE_EXECUTE, valueapi.NoValue

    @arguments("newframe2")
    def opimpl_inline_call_ir_i(self, _):
        return None, CHANGE_FRAME, valueapi.NoValue

    @arguments("label")
    def opimpl_goto(self, target):
        self.pc = target
        return None, CONTINUE_EXECUTE, valueapi.NoValue
        
    @arguments("box")
    def opimpl_int_return(self, b):
        # TODO
        controlflow, return_value = self.metainterp.finishframe(b)
        return None, controlflow, return_value
    
    @arguments("box", "box")
    def opimpl_strgetitem(self, strbox, indexbox):
        s = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), valueapi.get_value_ref(strbox))
        res = ord(s.chars[valueapi.get_value_int(indexbox)])
        if (valueapi.is_constant(strbox) and valueapi.is_constant(indexbox)):
            return valueapi.create_const(res), CONTINUE_EXECUTE, valueapi.NoValue
        return self.metainterp.history.record2(rop.STRGETITEM, strbox, indexbox, res), CONTINUE_EXECUTE, valueapi.NoValue
    
    @arguments("box", "descr", "orgpc")
    def opimpl_switch(self, valuebox, switchdict, orgpc):
        search_value = valueapi.get_value_int(valuebox)
        assert isinstance(switchdict, SwitchDictDescr)
        try:
            target = switchdict.dict[search_value]
        except KeyError:
            # TODO
            pass
        if not valueapi.is_constant(valuebox):
            if valueapi.get_type(valuebox) == TYPE_INT:
                promoted_box = valueapi.create_const(valueapi.get_value_int(valuebox))
            elif valueapi.get_type(valuebox) == TYPE_FLOAT:
                promoted_box = valueapi.create_const(valueapi.get_value_float(valuebox))
            elif valueapi.get_type(valuebox) == TYPE_REF:
                promoted_box = valueapi.create_const(valueapi.get_value_ref(valuebox))
            self.generate_guard(rop.GUARD_VALUE, valuebox, resumepc=orgpc)
            self.metainterp.replace_box(valuebox, promoted_box)
        self.pc = target
        return None, CONTINUE_EXECUTE, valueapi.NoValue

    def not_implemented(self, *args):
        name = self.metainterp.metainterp_sd.opcode_names[ord(self.bytecode[self.pc])]
        print "bytecode", name, "not implemented"
        if not we_are_translated():
            import pdb; pdb.set_trace()
        raise NotImplementedError(name)
    
    def fill_registers(self, f, length, position, argcode):
        assert argcode in 'IRF'
        code = self.bytecode
        if argcode == 'I':
            for i in range(length):
                index = ord(code[position+i])
                value = self.fetch_register_value('i', index)
                f.set_reg_i(i, value)
        elif argcode == 'R':
            for i in range(length):
                index = ord(code[position+i])
                value = self.fetch_register_value('r', index)
                f.set_reg_r(i, value)
        else:
            assert argcode == 'F'
            for i in range(length):
                index = ord(code[position+i])
                value = self.fetch_register_value('f', index)
                f.set_reg_f(i, value)
                
    @specialize.arg(1)
    def fetch_register_value(self, argcode, index):
        jitcode = self.jitcode
        if argcode == 'i':
            if index >= jitcode.num_regs_i():
                value = valueapi.create_const(jitcode.constants_i[index - jitcode.num_regs_i()])
            else:
                value = self.get_reg_i(index)
        elif argcode == 'r':
            if index >= jitcode.num_regs_r():
                value = valueapi.create_const(jitcode.constants_r[index - jitcode.num_regs_r()])
            else:
                value = self.get_reg_r(index)
        elif argcode == 'f':
            if index >= jitcode.num_regs_f():
                # TODO value = jitcode.constants_f[index - jitcode.num_regs_f()]
                assert False
            else:
                value = self.get_reg_f(index)
        else:
            raise AssertionError("bad argcode")
        
        return value

class MetaInterp(object):
    def __init__(self, metainterp_sd):
        self.framestack = []
        self.metainterp_sd = metainterp_sd

        # total amount of registers to allocate from, will be increased if necessary 
        # TODO good initial size?
        self.max_regs = 256

        # top of current allocation stack, place of next allocation
        self.allocated_regs = 0

        # lists of registers, both in use and free
        self.regs = [valueapi.NoValue] * self.max_regs
        self.return_value = valueapi.NoValue

    def alloc_regs(self, num_regs):
        # ensure enough space available for new frame
        did_resize = False
        while self.allocated_regs + num_regs > self.max_regs:
            self.max_regs *= 2
            did_resize = True
        if did_resize:
            new_regs = [valueapi.NoValue] * self.max_regs
            # copy over old values
            for i in range(self.allocated_regs):
                new_regs[i] = self.regs[i]
            self.regs = new_regs
        # allocate
        res = self.allocated_regs
        self.allocated_regs += num_regs
        return res

    def free_regs(self, num_regs):
        self.allocated_regs -= num_regs

    def create_empty_history(self, inputargs):
        self.history = History(len(inputargs), self.metainterp_sd)
        self.history.set_inputargs(inputargs)

    def replace_box(self, oldbox, newbox):
        for i in range(self.allocated_regs):
            if self.regs[i] is oldbox:
                self.regs[i] = newbox
        # TODO virtual refs
        # TODO heapcache

    def compile_and_run_once(self, jitdriver_sd, *args):
        self.jitdriver_sd = jitdriver_sd
        original_boxes = self.initialize_original_boxes(jitdriver_sd, *args)
        self.initialize_state_from_start(original_boxes)
        num_green_args = jitdriver_sd.num_green_args
        self.create_empty_history(original_boxes[num_green_args:],)
        self.interpret()

    @specialize.arg(1)
    def initialize_original_boxes(self, jitdriver_sd, *args):
        original_boxes = [valueapi.NoValue] * len(args)
        self._fill_original_boxes(jitdriver_sd, original_boxes, 0,
                                  *args)
        return original_boxes

    @specialize.arg(1)
    @always_inline
    def _fill_original_boxes(self, jitdriver_sd, original_boxes,
                             position, *args):
        if args:
            box = wrap(args[0], position - self.jitdriver_sd.num_green_args)
            original_boxes[position] = box
            self._fill_original_boxes(jitdriver_sd, original_boxes,
                                      position + 1, *args[1:])

    def initialize_state_from_start(self, original_boxes):
        self.framestack = []
        f = self.newframe(self.jitdriver_sd.mainjitcode)
        f.setup_call(original_boxes)

    def newframe(self, jitcode):
        f = MIFrame(self, jitcode)
        self.framestack.append(f)
        return f
    
    def finishframe(self, return_value):
        frame = self.framestack.pop()

        # free allocated registers
        self.free_regs(frame.jitcode.num_regs_i() 
                       + frame.jitcode.num_regs_r() 
                       + frame.jitcode.num_regs_f())

        if self.framestack:
            # TODO other return types
            cur = self.framestack[-1]
            target_index = ord(cur.bytecode[cur.pc-1])
            cur.set_reg_i(target_index, return_value)
            return CHANGE_FRAME, valueapi.NoValue
        else:
            return DONE_WITH_FRAME_INT, return_value

    def interpret(self):
        # Execute the frames forward until we raise a DoneWithThisFrame,
        # a ExitFrameWithException, or a ContinueRunningNormally exception.
        while True:
            controlflow, return_value = self.framestack[-1].run_one_step()
            if controlflow == DONE_WITH_FRAME_INT:
                self.return_value = return_value
                return


@specialize.ll()
def wrap(value, inputarg_position_or_neg):
    assert isinstance(value, int)
    if inputarg_position_or_neg < 0:
        return valueapi.create_const(value)
    else:
        return valueapi.create_box(inputarg_position_or_neg, value)

def miniinterp_staticdata(metainterp_sd, cw):
    # replace the opcode_names and opcode_implementations
    insns = cw.assembler.insns
    metainterp_sd.opcode_names = ['?'] * len(insns)
    metainterp_sd.opcode_implementations = [None] * len(insns)
    for key, value in insns.items():
        assert metainterp_sd.opcode_implementations[value] is None
        metainterp_sd.opcode_names[value] = key
        name, argcodes = key.split('/')
        opimpl = _get_opimpl_method(name, argcodes)
        metainterp_sd.opcode_implementations[value] = opimpl
    unrolling_opcode_implementations = unrolling_iterable(enumerate(metainterp_sd.opcode_implementations))
    @always_inline
    def run_one_step(self):
        while True:
            pc = self.pc
            op = ord(self.bytecode[pc])
            if not we_are_translated():
                controlflow, return_value = metainterp_sd.opcode_implementations[op](self, pc)
                if controlflow != CONTINUE_EXECUTE:
                    return controlflow, return_value
            else:
                for opcode_num, handler in unrolling_opcode_implementations:
                    if opcode_num == op:
                        controlflow, return_value = handler(self, pc)
                        if controlflow != CONTINUE_EXECUTE:
                            return controlflow, return_value
                        break
        
    metainterp_sd.run_one_step = run_one_step
    metainterp_sd.op_live = insns.get('live/', -1)

def _get_opimpl_method(name, argcodes):
    from rpython.jit.metainterp.blackhole import signedord
    @always_inline
    def handler(self, position):
        assert position >= 0
        args = ()
        next_argcode = 0
        code = self.bytecode
        orgpc = position
        position += 1
        for argtype in argtypes:
            if argtype == "box":     # a box, of whatever type
                argcode = argcodes[next_argcode]
                next_argcode = next_argcode + 1

                if argcode == 'c':
                    value = valueapi.create_const(signedord(code[position]))
                else:
                    index = ord(code[position])
                    value = self.fetch_register_value(argcode, index)
                
                position += 1
            elif argtype == "descr" or argtype == "jitcode":
                assert argcodes[next_argcode] == 'd'
                next_argcode = next_argcode + 1
                index = ord(code[position]) | (ord(code[position+1])<<8)
                value = self.metainterp.metainterp_sd.opcode_descrs[index]
                if argtype == "jitcode":
                    assert isinstance(value, JitCode)
                position += 2
            elif argtype == "label":
                assert argcodes[next_argcode] == 'L'
                next_argcode = next_argcode + 1
                value = ord(code[position]) | (ord(code[position+1])<<8)
                position += 2
            elif argtype == "boxes":     # a list of boxes of some type
                assert 0, "unsupported"
            elif argtype == "boxes2":     # two lists of boxes merged into one
                assert 0, "unsupported"
            elif argtype == "boxes3":    # three lists of boxes merged into one
                assert 0, "unsupported"
            elif argtype == "newframe" or argtype == "newframe2" or argtype == "newframe3":
                # this and the next two are basically equivalent to
                # jitcode boxes/boxes2/boxes3
                # instead of allocating the list of boxes, just put everything
                # into the correct position of a new MIFrame

                # first get the jitcode
                assert argcodes[next_argcode] == 'd'
                next_argcode = next_argcode + 1
                index = ord(code[position]) | (ord(code[position+1])<<8)
                jitcode = self.metainterp.metainterp_sd.opcode_descrs[index]
                assert isinstance(jitcode, JitCode)
                position += 2
                # make a new frame
                value = self.metainterp.newframe(jitcode)
                value.pc = 0

                # now put boxes into the right places
                length = ord(code[position])
                self.fill_registers(value, length, position + 1,
                                    argcodes[next_argcode])
                next_argcode = next_argcode + 1
                position += 1 + length
                if argtype != "newframe": # 2/3 lists of boxes
                    length = ord(code[position])
                    self.fill_registers(value, length, position + 1,
                                        argcodes[next_argcode])
                    next_argcode = next_argcode + 1
                    position += 1 + length
                if argtype == "newframe3": # 3 lists of boxes
                    length = ord(code[position])
                    self.fill_registers(value, length, position + 1,
                                        argcodes[next_argcode])
                    next_argcode = next_argcode + 1
                    position += 1 + length
            elif argtype == "orgpc":
                value = orgpc
            elif argtype == "int":
                assert 0, "unsupported"
            elif argtype == "jitcode_position":
                assert 0, "unsupported"
            else:
                raise AssertionError("bad argtype: %r" % (argtype,))
            args += (value,)
        #
        num_return_args = len(argcodes) - next_argcode
        assert num_return_args == 0 or num_return_args == 2
        if num_return_args:
            # Save the type of the resulting box.  This is needed if there is
            # a get_list_of_active_boxes().  See comments there.
            self._result_argcode = argcodes[next_argcode + 1]
            position += 1
        else:
            self._result_argcode = 'v'
        self.pc = position
        #
        if not we_are_translated():
            if self.debug:
                print '\tpyjitpl: %s(%s)' % (name, ', '.join(map(repr, args))),
            try:
                resultbox, controlflow, return_value = unboundmethod(self, *args)
            except Exception as e:
                if self.debug:
                    print '-> %s!' % e.__class__.__name__
                raise
            if num_return_args == 0:
                if self.debug:
                    print
                assert resultbox is None
            else:
                if self.debug:
                    print '-> %r' % (resultbox,)
                assert argcodes[next_argcode] == '>'
                result_argcode = argcodes[next_argcode + 1]
        else:
            resultbox, controlflow, return_value = unboundmethod(self, *args)
        #
        if resultbox is not None:
            target_index = ord(self.bytecode[self.pc-1])
            self.set_reg_i(target_index, resultbox) # TODO only ints supported so far
        return controlflow, return_value
    #
    if not hasattr(MIFrame, 'opimpl_' + name):
        return MIFrame.not_implemented.im_func
    unboundmethod = getattr(MIFrame, 'opimpl_' + name).im_func
    argtypes = unrolling_iterable(unboundmethod.argtypes)
    handler.__name__ = 'handler_' + name
    return handler

def target(driver, *args):
    from rpython.rlib import jit
    from rpython.jit.backend.llgraph import runner
    from rpython.jit.metainterp.test import support
    from rpython.jit.metainterp import pyjitpl, history, jitexc
    driver.config.translation.taggedpointers = True
    def function(bytecode_choice, init):
        if bytecode_choice == 1:
            bytecode = "+" * 1000000 + "-" * 999999 + "r"
        else:
            bytecode = "r"
        pc = 0
        acc = init
        while pc < len(bytecode):
            opcode = bytecode[pc]
            if opcode == "+":
                acc += 1
            if opcode == "-":
                acc -= 1
            if opcode == "r":
                return acc
            pc += 1
        return acc
    class self:
        pass
    stats = support._get_jitcodes(self, runner.LLGraphCPU, function, [1, 0])
    cw = self.cw
    opt = history.Options(listops=True)
    metainterp_sd = pyjitpl.MetaInterpStaticData(cw.cpu, opt)
    stats.metainterp_sd = metainterp_sd
    metainterp_sd.finish_setup(cw)
    metainterp_sd.finish_setup_descrs()

    [jitdriver_sd] = metainterp_sd.jitdrivers_sd
    miniinterp_staticdata(metainterp_sd, cw)

    def bench_main(args):
        import time
        t1 = time.time()
        metainterp = MetaInterp(metainterp_sd)
        jitdriver_sd, = metainterp_sd.jitdrivers_sd
        metainterp.compile_and_run_once(jitdriver_sd, 1, 0)    
        t2 = time.time()
        print t2 - t1
        #print valueapi.get_value_int(metainterp.return_value)
        return 0
    return bench_main
