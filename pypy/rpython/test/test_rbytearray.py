
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin
from pypy.rpython.lltypesystem.rbytearray import hlbytearray

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
