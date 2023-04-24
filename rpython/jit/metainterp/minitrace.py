from rpython.jit.metainterp.resoperation import rop
from rpython.jit.metainterp import history
from rpython.jit.metainterp.pyjitpl import arguments
from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib.objectmodel import we_are_translated, specialize, always_inline
from rpython.jit.codewriter.liveness import OFFSET_SIZE

class ChangeFrame(Exception):
    pass


class AbstractValue(object):
    def is_constant(self):
        return False

class FrontendOp(AbstractValue):
    pass

class IntFrontendOp(FrontendOp):
    type = history.INT

    def __init__(self, position_and_flags, _resint):
        self.position_and_flags = position_and_flags
        self._resint = _resint

    def getint(self):
        return self._resint

class Const(AbstractValue):
    def is_constant(self):
        return True

class ConstInt(Const):
    type = history.INT

    def __init__(self, value):
        self.value = value

    def getint(self):
        return self.value

class History(object):
    def __init__(self):
        self.trace = []
        self.snapshots = []

    def set_inputargs(self, inputargs, metainterp_sd):
        for i, arg in enumerate(inputargs):
            arg.position_and_flags = i
        self.num_inputargs = len(inputargs)

    def record(self, opnum, argboxes, value, descr=None):
        pos = len(self.trace) + self.num_inputargs
        op = self._make_op(pos, value)
        self.trace.append((opnum, argboxes, descr))
        return op

    def _make_op(self, pos, value):
        if value is None:
            return None
        return IntFrontendOp(pos, value)

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

    def setup_call(self, argboxes):
        self.pc = 0
        count_i = count_r = count_f = 0
        for box in argboxes:
            # XXX only ints so far
            self.registers_i[count_i] = box
            count_i += 1

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
            raise # TODO

    def generate_guard(self, opnum, box=None, extraarg=None, resumepc=-1):
        if isinstance(box, Const):    # no need for a guard
            return
        guard_op = self.metainterp.history.record(opnum, box, None) # TODO
        
        # unrealistic implementation of snapshots
        self.metainterp.history.snapshots.append(self.metainterp.snapshot())


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

    @arguments("label")
    def opimpl_goto(self, target):
        self.pc = target
        
    @arguments("box")
    def opimpl_int_return(self, b):
        # TODO
        self.return_value = b
        raise ChangeFrame

    def not_implemented(self, *args):
        name = self.metainterp.metainterp_sd.opcode_names[ord(self.bytecode[self.pc])]
        import pdb; pdb.set_trace()
        raise NotImplementedError(name)

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

    def interpret(self):
        # Execute the frames forward until we raise a DoneWithThisFrame,
        # a ExitFrameWithException, or a ContinueRunningNormally exception.
        try:
            while True:
                self.framestack[-1].run_one_step()
        except Exception:
            pass # TODO


def wrap(value, in_const_box=False):
    assert isinstance(value, int)
    if in_const_box:
        return ConstInt(value)
    else:
        return IntFrontendOp(0, value)


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
                assert 0, "unsupported"
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

