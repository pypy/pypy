
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin
from pypy.rpython.lltypesystem.rbytearray import hlbytearray
from pypy.rpython.annlowlevel import llstr, hlstr

class TestByteArray(BaseRtypingTest, LLRtypeMixin):
    def test_bytearray_creation(self):
        def f(x):
            if x:
                b = bytearray(str(x))
            else:
                b = bytearray("def")
            return b
        ll_res = self.interpret(f, [0])
        assert hlbytearray(ll_res) == "def"
        ll_res = self.interpret(f, [1])
        assert hlbytearray(ll_res) == "1"

    def test_addition(self):
        def f(x):
            return bytearray("a") + hlstr(x)

        ll_res = self.interpret(f, [llstr("def")])
        assert hlbytearray(ll_res) == "adef"

        def f2(x):
            return hlstr(x) + bytearray("a")

        ll_res = self.interpret(f2, [llstr("def")])
        assert hlbytearray(ll_res) == "defa"
