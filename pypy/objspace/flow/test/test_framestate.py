from py.test import raises
from pypy.objspace.flow.model import *
from pypy.interpreter.pycode import PyCode
from pypy.rlib.unroll import SpecTag
from pypy.objspace.flow.objspace import FlowObjSpace
from pypy.objspace.flow.flowcontext import FlowSpaceFrame

class TestFrameState:
    def setup_class(cls):
        cls.space = FlowObjSpace()

    def getframe(self, func):
        try:
            func = func.im_func
        except AttributeError:
            pass
        frame = FlowSpaceFrame(self.space, func)
        # hack the frame
        frame.locals_stack_w[frame.pycode.co_nlocals-1] = Constant(None)
        return frame

    def func_simple(x):
        spam = 5
        return spam

    def test_eq_framestate(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        fs2 = frame.getstate()
        assert fs1 == fs2

    def test_neq_hacked_framestate(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        frame.locals_stack_w[frame.pycode.co_nlocals-1] = Variable()
        fs2 = frame.getstate()
        assert fs1 != fs2

    def test_union_on_equal_framestates(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        fs2 = frame.getstate()
        assert fs1.union(fs2) == fs1

    def test_union_on_hacked_framestates(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        frame.locals_stack_w[frame.pycode.co_nlocals-1] = Variable()
        fs2 = frame.getstate()
        assert fs1.union(fs2) == fs2  # fs2 is more general
        assert fs2.union(fs1) == fs2  # fs2 is more general

    def test_restore_frame(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        frame.locals_stack_w[frame.pycode.co_nlocals-1] = Variable()
        frame.setstate(fs1)
        assert fs1 == frame.getstate()

    def test_copy(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        fs2 = fs1.copy()
        assert fs1 == fs2

    def test_getvariables(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        vars = fs1.getvariables()
        assert len(vars) == 1

    def test_getoutputargs(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        frame.locals_stack_w[frame.pycode.co_nlocals-1] = Variable()
        fs2 = frame.getstate()
        outputargs = fs1.getoutputargs(fs2)
        # 'x' -> 'x' is a Variable
        # locals_w[n-1] -> locals_w[n-1] is Constant(None)
        assert outputargs == [frame.locals_stack_w[0], Constant(None)]

    def test_union_different_constants(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        frame.locals_stack_w[frame.pycode.co_nlocals-1] = Constant(42)
        fs2 = frame.getstate()
        fs3 = fs1.union(fs2)
        frame.setstate(fs3)
        assert isinstance(frame.locals_stack_w[frame.pycode.co_nlocals-1],
                          Variable)   # generalized

    def test_union_spectag(self):
        frame = self.getframe(self.func_simple)
        fs1 = frame.getstate()
        frame.locals_stack_w[frame.pycode.co_nlocals-1] = Constant(SpecTag())
        fs2 = frame.getstate()
        assert fs1.union(fs2) is None   # UnionError
