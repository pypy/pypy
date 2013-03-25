from rpython.rtyper.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from rpython.rlib.rstruct.runpack import runpack
from rpython.rlib.rarithmetic import LONG_BIT
import struct

class BaseTestRStruct(BaseRtypingTest):
    def test_unpack(self):
        pad = '\x00' * (LONG_BIT//8-1)    # 3 or 7 null bytes
        def fn():
            return runpack('sll', 'a'+pad+'\x03'+pad+'\x04'+pad)[1]
        assert fn() == 3
        assert self.interpret(fn, []) == 3

    def test_unpack_2(self):
        data = struct.pack('iiii', 0, 1, 2, 4)
        def fn():
            a, b, c, d = runpack('iiii', data)
            return a * 1000 + b * 100 + c * 10 + d
        assert fn() == 124
        assert self.interpret(fn, []) == 124

    def test_unpack_single(self):
        data = struct.pack('i', 123)
        def fn():
            return runpack('i', data)
        assert fn() == 123
        assert self.interpret(fn, []) == 123

class TestLLType(BaseTestRStruct, LLRtypeMixin):
    pass

class TestOOType(BaseTestRStruct, OORtypeMixin):
    pass
