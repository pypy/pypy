
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rlib.rstruct.runpack import runpack
import struct

class BaseTestRStruct(BaseRtypingTest):
    def test_unpack(self):
        def fn():
            return runpack('sll', 'a\x00\x00\x00\x03\x00\x00\x00\x04\x00\x00\x00')[1]
        assert fn() == 3
        assert self.interpret(fn, []) == 3

    def test_unpack_2(self):
        py.test.skip("Fails")
        data = struct.pack('iiii', 0, 1, 2, 4)
        
        def fn():
            a, b, c, d = runpack('iiii', data)
            return a * 1000 + b * 100 + c * 10 + d

        assert fn() == 124
        assert self.interpret(fn, []) == 124

class TestLLType(BaseTestRStruct, LLRtypeMixin):
    pass

class TestOOType(BaseTestRStruct, OORtypeMixin):
    pass
