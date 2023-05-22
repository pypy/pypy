from rpython.jit.codewriter.jitcode import JitCode, SwitchDictDescr
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp import history, jitexc, resume
from rpython.jit.metainterp.history import History
from rpython.jit.metainterp.pyjitpl import arguments
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import we_are_translated, specialize, always_inline
from rpython.jit.codewriter.liveness import OFFSET_SIZE
from rpython.jit.metainterp.valueapi import valueapi
from rpython.rtyper.lltypesystem import lltype, rstr

class ChangeFrame(Exception):
    pass

class DoneWithThisFrameInt(Exception):
    def __init__(self, result):
        self.result = result

class MIFrame(object):
    debug = True

    def __init__(self, metainterp, jitcode):
        self.metainterp = metainterp
        self.jitcode = jitcode
        self.bytecode = jitcode.code

        # allocate registers
        self.registers_offset_i = self.metainterp.alloc_regs_i(jitcode.num_regs_i())
        self.registers_offset_r = self.metainterp.alloc_regs_r(jitcode.num_regs_r())
        self.registers_offset_f = self.metainterp.alloc_regs_f(jitcode.num_regs_f())
        
        self.return_value = None # TODO
        self.parent_snapshot = None

    def get_reg_i(self, index):
        return self.metainterp.regs_i[self.registers_offset_i + index]
    
    def get_reg_r(self, index):
        return self.metainterp.regs_r[self.registers_offset_r + index]
    
    def get_reg_f(self, index):
        return self.metainterp.regs_f[self.registers_offset_f + index]
    
    def set_reg_i(self, index, value):
        self.metainterp.regs_i[self.registers_offset_i + index] = value
    
    def set_reg_r(self, index, value):
        self.metainterp.regs_r[self.registers_offset_r + index] = value
    
    def set_reg_f(self, index, value):
        self.metainterp.regs_f[self.registers_offset_f+ index] = value

    def setup_call(self, argboxes):
        self.pc = 0
        count_i = count_r = count_f = 0
        for box in argboxes:
            if box.type == history.INT:
                self.set_reg_i(count_i, box)
                count_i += 1
            elif box.type == history.REF:
                self.set_reg_r(count_r, box)
                count_r += 1
            elif box.type == history.FLOAT:
                self.set_reg_f(count_f, box)
                count_f += 1
            else:
                raise AssertionError(box.type)

    def run_one_step(self):
        # Execute the frame forward.  This method contains a loop that leaves
        # whenever the 'opcode_implementations' (which is one of the 'opimpl_'
        # methods) raises ChangeFrame.  This is the case when the current frame
        # changes, due to a call or a return.
            staticdata = self.metainterp.metainterp_sd
            while True:
                pc = self.pc
                op = ord(self.bytecode[pc])
                if op == staticdata.op_live:
                    self.pc = pc + OFFSET_SIZE + 1
                else:
                    try:
                        staticdata.opcode_implementations[op](self, pc)
                    except ChangeFrame:
                        return

    def generate_guard(self, opnum, box=None, extraarg=None, resumepc=-1):
        if valueapi.is_constant(box):    # no need for a guard
            return
        guard_op = self.metainterp.history.record(opnum, [box], None) # TODO
        
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
                self.set_reg_i(index, history.CONST_FALSE)
            elif argcode == 'r':
                self.set_reg_r(index, history.CONST_NULL)
            elif argcode == 'f':
                self.set_reg_f(index, history.CONST_FZERO)
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
        res = valueapi.get_value(b1) + valueapi.get_value(b2)
        if not (valueapi.is_constant(b1) and valueapi.is_constant(b2)):
            res_box = self.metainterp.history.record(rop.INT_ADD, [b1, b2], res)
        else:
            res_box = valueapi.create_const(res)
        return res_box

    @arguments("box", "box")
    def opimpl_int_sub(self, b1, b2):
        res = valueapi.get_value(b1) - valueapi.get_value(b2)
        if not (valueapi.is_constant(b1) and valueapi.is_constant(b2)):
            res_box = self.metainterp.history.record(rop.INT_SUB, [b1, b2], res)
        else:
            res_box = valueapi.create_const(res)
        return res_box

    @arguments("box", "box")
    def opimpl_int_mul(self, b1, b2):
        res = valueapi.get_value(b1) * valueapi.get_value(b2)
        if not (valueapi.is_constant(b1) and valueapi.is_constant(b2)):
            res_box = self.metainterp.history.record(rop.INT_MUL, [b1, b2], res)
        else:
            res_box = valueapi.create_const(res)
        return res_box

    @arguments("box")
    def opimpl_int_copy(self, box):
        return box

    @arguments()
    def opimpl_live(self):
        self.pc += OFFSET_SIZE

    @arguments("box", "box", "label", "orgpc")
    def opimpl_goto_if_not_int_gt(self, a, b, target, orgpc):
        res = valueapi.get_value(a) > valueapi.get_value(b)
        if not (valueapi.is_constant(a) and valueapi.is_constant(b)):
            res_box = self.metainterp.history.record(rop.INT_GT, [a, b], res)
            if res:
                opnum = rop.GUARD_TRUE
            else:
                opnum = rop.GUARD_FALSE
            self.generate_guard(opnum, res_box, resumepc=orgpc)
        if not res:
            self.pc = target

    @arguments("box", "box", "label", "orgpc")
    def opimpl_goto_if_not_int_lt(self, a, b, target, orgpc):
        res = valueapi.get_value(a) < valueapi.get_value(b)
        if not (valueapi.is_constant(a) and valueapi.is_constant(b)):
            res_box = self.metainterp.history.record(rop.INT_LT, [a, b], res)
            if res:
                opnum = rop.GUARD_TRUE
            else:
                opnum = rop.GUARD_FALSE
            self.generate_guard(opnum, res_box, resumepc=orgpc)
        if not res:
            self.pc = target

    @arguments("box", "box", "label", "orgpc")
    def opimpl_goto_if_not_int_eq(self, a, b, target, orgpc):
        res = valueapi.get_value(a) == valueapi.get_value(b)
        if not (valueapi.is_constant(a) and valueapi.is_constant(b)):
            res_box = self.metainterp.history.record(rop.INT_EQ, [a, b], res)
            if res:
                opnum = rop.GUARD_TRUE
            else:
                opnum = rop.GUARD_FALSE
            self.generate_guard(opnum, res_box, resumepc=orgpc)
        if not res:
            self.pc = target

    @arguments("newframe2")
    def opimpl_inline_call_ir_i(self, _):
        raise ChangeFrame

    @arguments("label")
    def opimpl_goto(self, target):
        self.pc = target
        
    @arguments("box")
    def opimpl_int_return(self, b):
        # TODO
        self.return_value = b
        self.metainterp.finishframe()
    
    @arguments("box", "box")
    def opimpl_strgetitem(self, strbox, indexbox):
        s = lltype.cast_opaque_ptr(lltype.Ptr(rstr.STR), valueapi.get_value(strbox))
        res = ord(s.chars[valueapi.get_value(indexbox)])
        if (valueapi.is_constant(strbox) and valueapi.is_constant(indexbox)):
            return valueapi.create_const(res)
        return self.metainterp.history.record(rop.STRGETITEM, [strbox, indexbox], res)
    
    @arguments("box", "descr", "orgpc")
    def opimpl_switch(self, valuebox, switchdict, orgpc):
        search_value = valueapi.get_value(valuebox)
        assert isinstance(switchdict, SwitchDictDescr)
        try:
            target = switchdict.dict[search_value]
        except KeyError:
            # TODO
            pass
        if not valueapi.is_constant(valuebox):
            self.generate_guard(rop.GUARD_VALUE, valuebox, resumepc=orgpc)
        self.pc = target

    def not_implemented(self, *args):
        name = self.metainterp.metainterp_sd.opcode_names[ord(self.bytecode[self.pc])]
        print "bytecode", name, "not implemented"
        if not we_are_translated():
            import pdb; pdb.set_trace()
        raise NotImplementedError(name)
    
    def fill_registers(self, f, length, position, argcode, old_jitcode):
        assert argcode in 'IRF'
        code = self.bytecode
        for i in range(length):
            index = ord(code[position+i])
            value = self.fetch_register_value(argcode, index, old_jitcode)
            if   argcode == 'I':
                f.set_reg_i(i, value)
            elif argcode == 'R':
                f.set_reg_r(i, value)
            elif argcode == 'F':
                f.set_reg_f(i, value)
                
    @specialize.arg_or_var(1)
    def fetch_register_value(self, argcode, index, jitcode):
        if argcode.lower() == 'i':
            if index >= jitcode.num_regs_i():
                value = valueapi.create_const(jitcode.constants_i[index - jitcode.num_regs_i()])
            else:
                value = self.get_reg_i(index)
        elif argcode.lower() == 'r':
            if index >= jitcode.num_regs_r():
                value = valueapi.create_const(jitcode.constants_r[index - jitcode.num_regs_r()])
            else:
                value = self.get_reg_r(index)
        elif argcode.lower() == 'f':
            if index >= jitcode.num_regs_f():
                # TODO value = jitcode.constants_f[index - jitcode.num_regs_f()]
                value = None
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
        self.max_regs_i = 16
        self.max_regs_r = 16
        self.max_regs_f = 16

        # top of current allocation stack, place of next allocation
        self.allocated_regs_i = 0
        self.allocated_regs_r = 0
        self.allocated_regs_f = 0

        # lists of registers, both in use and free
        self.regs_i = [None] * self.max_regs_i
        self.regs_r = [None] * self.max_regs_r
        self.regs_f = [None] * self.max_regs_f

    def alloc_regs_i(self, num_regs_i):
        # ensure enough space available for new frame
        did_resize = False
        while self.allocated_regs_i + num_regs_i > self.max_regs_i:
            self.max_regs_i *= 2
            did_resize = True
        if did_resize:
            new_regs_i = [None] * self.max_regs_i
            # copy over old values
            for i in range(self.allocated_regs_i):
                new_regs_i[i] = self.regs_i[i]
            self.regs_i = new_regs_i
        # allocate
        res = self.allocated_regs_i
        self.allocated_regs_i += num_regs_i
        return res

    def alloc_regs_r(self, num_regs_r):
        # ensure enough space available for new frame
        did_resize = False
        while self.allocated_regs_r + num_regs_r > self.max_regs_r:
            self.max_regs_r *= 2
            did_resize = True
        if did_resize:
            new_regs_r = [None] * self.max_regs_r
            # copy over old values
            for i in range(self.allocated_regs_r):
                new_regs_r[i] = self.regs_r[i]
            self.regs_r = new_regs_r
        # allocate
        res = self.allocated_regs_r
        self.allocated_regs_r += num_regs_r
        return res
    
    def alloc_regs_f(self, num_regs_f):
        # ensure enough space available for new frame
        did_resize = False
        while self.allocated_regs_f + num_regs_f > self.max_regs_f:
            self.max_regs_f *= 2
            did_resize = True
        if did_resize:
            new_regs_f = [None] * self.max_regs_f
            # copy over old values
            for i in range(self.allocated_regs_f):
                new_regs_f[i] = self.regs_f[i]
            self.regs_f = new_regs_f
        # allocate
        res = self.allocated_regs_f
        self.allocated_regs_f += num_regs_f
        return res
    
    def free_regs_i(self, num_regs_i):
        self.allocated_regs_i -= num_regs_i

    def free_regs_r(self, num_regs_r):
        self.allocated_regs_r -= num_regs_r

    def free_regs_f(self, num_regs_f):
        self.allocated_regs_f -= num_regs_f

    def create_empty_history(self):
        self.history = History()

    def compile_and_run_once(self, jitdriver_sd, *args):
        self.jitdriver_sd = jitdriver_sd
        original_boxes = self.initialize_original_boxes(jitdriver_sd, *args)
        self.initialize_state_from_start(original_boxes)
        self.create_empty_history()
        num_green_args = jitdriver_sd.num_green_args
        self.history.set_inputargs(original_boxes[num_green_args:],
                                   self.metainterp_sd)
        self.interpret()

    @specialize.arg(1)
    def initialize_original_boxes(self, jitdriver_sd, *args):
        original_boxes = [None] * len(args)
        self._fill_original_boxes(jitdriver_sd, original_boxes, 0,
                                  jitdriver_sd.num_green_args, *args)
        return original_boxes

    @specialize.arg(1)
    @always_inline
    def _fill_original_boxes(self, jitdriver_sd, original_boxes,
                             position,
                             num_green_args, *args):
        if args:
            box = wrap(args[0], num_green_args > 0)
            original_boxes[position] = box
            self._fill_original_boxes(jitdriver_sd, original_boxes,
                                      position + 1,
                                      num_green_args-1, *args[1:])

    def initialize_state_from_start(self, original_boxes):
        self.framestack = []
        f = self.newframe(self.jitdriver_sd.mainjitcode)
        f.setup_call(original_boxes)

    def newframe(self, jitcode):
        f = MIFrame(self, jitcode)
        self.framestack.append(f)
        return f
    
    def finishframe(self):
        frame = self.framestack.pop()

        # free allocated registers
        self.free_regs_i(frame.jitcode.num_regs_i())
        self.free_regs_r(frame.jitcode.num_regs_r())
        self.free_regs_f(frame.jitcode.num_regs_f())

        if self.framestack:
            # TODO other return types
            cur = self.framestack[-1]
            target_index = ord(cur.bytecode[cur.pc-1])
            cur.set_reg_i(target_index, frame.return_value)
            raise ChangeFrame
        else:
            raise DoneWithThisFrameInt(frame.return_value)

    def interpret(self):
        # Execute the frames forward until we raise a DoneWithThisFrame,
        # a ExitFrameWithException, or a ContinueRunningNormally exception.
        try:
            while True:
                self.framestack[-1].run_one_step()
        except DoneWithThisFrameInt as e:
            self.return_value = e.result


def wrap(value, in_const_box=False):
    assert isinstance(value, int)
    if in_const_box:
        return valueapi.create_const(value)
    else:
        op = valueapi.create_box(0, value)
        return op


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
    metainterp_sd.op_live = insns.get('live/', -1)

def _get_opimpl_method(name, argcodes):
    from rpython.jit.metainterp.blackhole import signedord
    #
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
                    value = self.fetch_register_value(argcode, index, self.jitcode)
                
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
                                    argcodes[next_argcode], self.jitcode)
                next_argcode = next_argcode + 1
                position += 1 + length
                if argtype != "newframe": # 2/3 lists of boxes
                    length = ord(code[position])
                    self.fill_registers(value, length, position + 1,
                                        argcodes[next_argcode], self.jitcode)
                    next_argcode = next_argcode + 1
                    position += 1 + length
                if argtype == "newframe3": # 3 lists of boxes
                    length = ord(code[position])
                    self.fill_registers(value, length, position + 1,
                                        argcodes[next_argcode], self.jitcode)
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
                resultbox = unboundmethod(self, *args)
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
                if 'ovf' not in name:
                    assert resultbox.type == {'i': history.INT,
                                              'r': history.REF,
                                              'f': history.FLOAT}[result_argcode]
        else:
            resultbox = unboundmethod(self, *args)
        #
        if resultbox is not None:
            target_index = ord(self.bytecode[self.pc-1])
            self.set_reg_i(target_index, resultbox) # TODO only ints supported so far
        elif not we_are_translated():
            assert self._result_argcode in 'v?' or 'ovf' in name
    #
    if not hasattr(MIFrame, 'opimpl_' + name):
        return MIFrame.not_implemented.im_func
    unboundmethod = getattr(MIFrame, 'opimpl_' + name).im_func
    argtypes = unrolling_iterable(unboundmethod.argtypes)
    handler.__name__ = 'handler_' + name
    return handler

def target(*args):
    from rpython.rlib import jit
    from rpython.jit.backend.llgraph import runner
    from rpython.jit.metainterp.test import support
    from rpython.jit.metainterp import pyjitpl, history, jitexc
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
        return 0
    return bench_main
