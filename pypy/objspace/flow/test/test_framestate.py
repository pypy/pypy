
import autopath

from pypy.objspace.flow.flowcontext import *
from pypy.objspace.flow.model import *
from pypy.interpreter.pycode import PyCode

objspacename = 'flow'

class TestFrameState:
    def getframe(self, func):
        space = self.space
        try:
            func = func.im_func
        except AttributeError:
            pass
        code = func.func_code
        code = PyCode(self.space)._from_code(code)
        w_globals = Constant({}) # space.newdict([])
        frame = code.create_frame(space, w_globals)

        formalargcount = code.getformalargcount()
        dummy = Constant(None)
        #dummy.dummy = True
        arg_list = ([Variable() for i in range(formalargcount)] +
                    [dummy] * (len(frame.fastlocals_w) - formalargcount))
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
        frame.fastlocals_w[-1] = Variable()
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
        frame.fastlocals_w[-1] = Variable()
        fs2 = FrameState(frame)
        assert fs1.union(fs2) == fs2  # fs2 is more general
        assert fs2.union(fs1) == fs2  # fs2 is more general

    def test_restore_frame(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        frame.fastlocals_w[-1] = Variable()
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
        frame.fastlocals_w[-1] = Variable()
        fs2 = FrameState(frame)
        outputargs = fs1.getoutputargs(fs2)
        # 'x' -> 'x' is a Variable
        # fastlocals_w[-1] -> fastlocals_w[-1] is Constant(None)
        assert outputargs == [frame.fastlocals_w[0], Constant(None)]

    def test_union_different_constants(self):
        frame = self.getframe(self.func_simple)
        fs1 = FrameState(frame)
        frame.fastlocals_w[-1] = Constant(42)
        fs2 = FrameState(frame)
        fs3 = fs1.union(fs2)
        fs3.restoreframe(frame)
        assert isinstance(frame.fastlocals_w[-1], Variable) # generalized
