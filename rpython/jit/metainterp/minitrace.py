from rpython.jit.codewriter.jitcode import JitCode
from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp import history, jitexc
from rpython.jit.metainterp.history import ConstPtrJitCode, ConstInt, IntFrontendOp, History, Const
from rpython.jit.metainterp.pyjitpl import arguments
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import we_are_translated, specialize, always_inline
from rpython.jit.codewriter.liveness import OFFSET_SIZE

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
        self.registers_i = [None] * 256
        self.registers_r = [None] * 256
        self.registers_f = [None] * 256
        self.return_value = None # TODO

        self.copy_constants(self.registers_i, jitcode.constants_i, ConstInt)
        self.copy_constants(self.registers_r, jitcode.constants_r, ConstPtrJitCode)
        # TODO self.copy_constants(self.registers_f, jitcode.constants_f, ConstFloat)

    @specialize.arg(3)
    def copy_constants(self, registers, constants, ConstClass):
        """Copy jitcode.constants[0] to registers[255],
                jitcode.constants[1] to registers[254],
                jitcode.constants[2] to registers[253], etc."""
        i = len(constants) - 1
        while i >= 0:
            j = 255 - i
            assert j >= 0
            registers[j] = ConstClass(constants[i])
            i -= 1

    def setup_call(self, argboxes):
        self.pc = 0
        count_i = count_r = count_f = 0
        for box in argboxes:
            if box.type == history.INT:
                self.registers_i[count_i] = box
                count_i += 1
            elif box.type == history.REF:
                self.registers_r[count_r] = box
                count_r += 1
            elif box.type == history.FLOAT:
                self.registers_f[count_f] = box
                count_f += 1
            else:
                raise AssertionError(box.type)

    def run_one_step(self):
        # Execute the frame forward.  This method contains a loop that leaves
        # whenever the 'opcode_implementations' (which is one of the 'opimpl_'
        # methods) raises ChangeFrame.  This is the case when the current frame
        # changes, due to a call or a return.
        try:
            staticdata = self.metainterp.metainterp_sd
            while True:
                pc = self.pc
                op = ord(self.bytecode[pc])
                staticdata.opcode_implementations[op](self, pc)
        except ChangeFrame:
            pass

    def generate_guard(self, opnum, box=None, extraarg=None, resumepc=-1):
        if isinstance(box, Const):    # no need for a guard
            return
        guard_op = self.metainterp.history.record(opnum, [box], None) # TODO
        
        # unrealistic implementation of snapshots
        # TODO reimpl 
        # self.metainterp.history.snapshots.append(self.metainterp.snapshot())


    @arguments("box", "box")
    def opimpl_int_add(self, b1, b2):
        res = b1.getint() + b2.getint()
        if not (b1.is_constant() and b2.is_constant()):
            res_box = self.metainterp.history.record(rop.INT_ADD, [b1, b2], res)
        else:
            res_box = ConstInt(res)
        return res_box

    @arguments("box", "box")
    def opimpl_int_sub(self, b1, b2):
        res = b1.getint() - b2.getint()
        if not (b1.is_constant() and b2.is_constant()):
            res_box = self.metainterp.history.record(rop.INT_SUB, [b1, b2], res)
        else:
            res_box = ConstInt(res)
        return res_box

    @arguments("box", "box")
    def opimpl_int_mul(self, b1, b2):
        res = b1.getint() * b2.getint()
        if not (b1.is_constant() and b2.is_constant()):
            res_box = self.metainterp.history.record(rop.INT_MUL, [b1, b2], res)
        else:
            res_box = ConstInt(res)
        return res_box

    @arguments("box")
    def opimpl_int_copy(self, box):
        return box

    @arguments()
    def opimpl_live(self):
        self.pc += OFFSET_SIZE

    @arguments("box", "box", "label", "orgpc")
    def opimpl_goto_if_not_int_gt(self, a, b, target, orgpc):
        res = a.getint() > b.getint()
        if not (a.is_constant() and b.is_constant()):
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
        res = a.getint() < b.getint()
        if not (a.is_constant() and b.is_constant()):
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
        res = a.getint() == b.getint()
        if not (a.is_constant() and b.is_constant()):
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
        res = ord(strbox._get_str()[indexbox.getint()])
        return self.metainterp.history.record(rop.STRGETITEM, [strbox, indexbox], res)

    def not_implemented(self, *args):
        name = self.metainterp.metainterp_sd.opcode_names[ord(self.bytecode[self.pc])]
        print "bytecode", name, "not implemented"
        if not we_are_translated():
            import pdb; pdb.set_trace()
        raise NotImplementedError(name)
    
    def fill_registers(self, f, length, position, argcode):
        assert argcode in 'IRF'
        code = self.bytecode
        for i in range(length):
            index = ord(code[position+i])
            if   argcode == 'I':
                reg = self.registers_i[index]
                f.registers_i[i] = reg
            elif argcode == 'R':
                reg = self.registers_r[index]
                f.registers_r[i] = reg
            elif argcode == 'F':
                reg = self.registers_f[index]
                f.registers_f[i] = reg
            else:
                raise AssertionError(argcode)


class MetaInterp(object):
    def __init__(self, metainterp_sd):
        self.framestack = []
        self.metainterp_sd = metainterp_sd

    def snapshot(self):
        res = []
        for frame in self.framestack:
            res.append((frame.jitcode, frame.pc, frame.registers_i[:], frame.registers_r[:], frame.registers_f[:]))
        return res

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
        if self.framestack:
            # TODO other return types
            cur = self.framestack[-1]
            target_index = ord(cur.bytecode[cur.pc-1])
            cur.registers_i[target_index] = frame.return_value
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
        return ConstInt(value)
    else:
        op = IntFrontendOp(0)
        op.setint(value)
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
                if argcode == 'i':
                    value = self.registers_i[ord(code[position])]
                elif argcode == 'c':
                    value = ConstInt(signedord(code[position]))
                elif argcode == 'r':
                    value = self.registers_r[ord(code[position])]
                elif argcode == 'f':
                    value = self.registers_f[ord(code[position])]
                else:
                    raise AssertionError("bad argcode")
                position += 1
            elif argtype == "descr" or argtype == "jitcode":
                assert 0, "unsupported"
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
            self.registers_i[target_index] = resultbox # XXX only ints supported so far
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
