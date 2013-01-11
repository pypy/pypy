from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.stm.test.transform2_support import BaseTestTransform
from pypy.rlib.jit import JitDriver


class TestJitDriver(BaseTestTransform):
    do_jit_driver = True

    def test_loop_no_arg(self):
        class X:
            counter = 10
        x = X()
        myjitdriver = JitDriver(greens=[], reds=[])

        def f1():
            while x.counter > 0:
                myjitdriver.jit_merge_point()
                x.counter -= 1
            return 'X'

        res = self.interpret(f1, [])
        assert res == 'X'
