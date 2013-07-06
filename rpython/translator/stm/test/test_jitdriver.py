from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.stm.test.transform_support import BaseTestTransform
from rpython.rlib.jit import JitDriver


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

    def test_loop_args(self):
        class X:
            counter = 100
        x = X()
        myjitdriver = JitDriver(greens=['a'], reds=['b', 'c'])

        def f1(a, b, c):
            while x.counter > 0:
                myjitdriver.jit_merge_point(a=a, b=b, c=c)
                x.counter -= (ord(a) + rffi.cast(lltype.Signed, b) + c)
            return 'X'

        res = self.interpret(f1, ['\x03', rffi.cast(rffi.SHORT, 4), 2])
        assert res == 'X'

    def test_loop_void_result(self):
        class X:
            counter = 10
        x = X()
        myjitdriver = JitDriver(greens=[], reds=[])

        def f1():
            while x.counter > 0:
                myjitdriver.jit_merge_point()
                x.counter -= 1

        res = self.interpret(f1, [])
        assert res == None
