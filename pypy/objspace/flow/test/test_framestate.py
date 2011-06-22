

from py.test import raises
from pypy.objspace.flow.model import *
from pypy.objspace.flow.framestate import *
from pypy.interpreter.pycode import PyCode
from pypy.objspace.flow.objspace import FlowObjSpace

class TestFrameState:
    def setup_class(cls):
        cls.space = FlowObjSpace() 

    def getframe(self, func):
        space = self.space
        try:
            func = func.im_func
        except AttributeError:
            pass
        code = func.func_code
        code = PyCode._from_code(self.space, code)
        w_globals = Constant({}) # space.newdict()
        frame = self.space.createframe(code, w_globals)

        formalargcount = code.getformalargcount()
        dummy = Constant(None)
        #dummy.dummy = True
        arg_list = ([Variable() for i in range(formalargcount)] +
                    [dummy] * (frame.nlocals - formalargcount))
        frame.setfastscope(arg_list)
        return frame

    def func_simple(x):
        spam = 5
        return spam

    def test_eq_framestate(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        fs2 = FrameState(frame)
        assert fs1 == fs2

    def test_neq_hacked_framestate(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        frame.locals_stack_w[frame.nlocals-1] = Variable()
        fs2 = FrameState(frame)
        assert fs1 != fs2

    def test_union_on_equal_framestates(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        fs2 = FrameState(frame)
        assert fs1.union(fs2) == fs1

    def test_union_on_hacked_framestates(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        frame.locals_stack_w[frame.nlocals-1] = Variable()
        fs2 = FrameState(frame)
        assert fs1.union(fs2) == fs2  # fs2 is more general
        assert fs2.union(fs1) == fs2  # fs2 is more general

    def test_restore_frame(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        frame.locals_stack_w[frame.nlocals-1] = Variable()
        fs1.restoreframe(frame)
        assert fs1 == FrameState(frame)

    def test_copy(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        fs2 = fs1.copy()
        assert fs1 == fs2

    def test_getvariables(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        vars = fs1.getvariables()
        assert len(vars) == 1 

    def test_getoutputargs(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        frame.locals_stack_w[frame.nlocals-1] = Variable()
        fs2 = FrameState(frame)
        outputargs = fs1.getoutputargs(fs2)
        # 'x' -> 'x' is a Variable
        # locals_w[n-1] -> locals_w[n-1] is Constant(None)
        assert outputargs == [frame.locals_stack_w[0], Constant(None)]

    def test_union_different_constants(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        frame.locals_stack_w[frame.nlocals-1] = Constant(42)
        fs2 = FrameState(frame)
        fs3 = fs1.union(fs2)
        fs3.restoreframe(frame)
        assert isinstance(frame.locals_stack_w[frame.nlocals-1], Variable)
                                 # ^^^ generalized

    def test_union_spectag(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        frame.locals_stack_w[frame.nlocals-1] = Constant(SpecTag())
        fs2 = FrameState(frame)
        assert fs1.union(fs2) is None   # UnionError
