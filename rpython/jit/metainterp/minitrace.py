from rpython.jit.metainterp.resoperation import rop

class AbstractValue(object):
    def is_constant(self):
        return False

class FrontendOp(AbstractValue):
    pass

class IntFrontendOp(FrontendOp):
    def __init__(self, position_and_flags, _resint):
        self.position_and_flags = position_and_flags
        self._resint = _resint

    def getint(self):
        return self._resint

class Const(AbstractValue):
    def is_constant(self):
        return True

class ConstInt(Const):
    def __init__(self, value):
        self.value = value

    def getint(self):
        return self.value

class History(object):
    def __init__(self, num_inputargs):
        self.trace = []
        self.num_inputargs = num_inputargs

    def record(self, opnum, argboxes, value, descr=None):
        pos = len(self.trace) + self.num_inputargs
        op = self._make_op(pos, value)
        self.trace.append((opnum, argboxes, descr))
        return op

    def _make_op(self, pos, value):
        return IntFrontendOp(pos, value)

class MIFrame(object):
    def __init__(self, metainterp):
        self.metainterp = metainterp
        self.registers_i = [None] * 256
        self.registers_r = [None] * 256
        self.registers_f = [None] * 256

    def opimpl_int_add(self, index1, index2, res_index):
        b1 = self.registers_i[index1]
        b2 = self.registers_i[index2]
        res = b1.getint() + b2.getint()
        if not (b1.is_constant() and b2.is_constant()):
            res_box = self.metainterp.history.record(rop.INT_ADD, [b1, b2], res)
        else:
            res_box = ConstInt(res)
        self.registers_i[res_index] = res_box
        return res_box

class MetaInterp(object):
    def __init__(self, history):
        self.history = history
        self.framestack = []
