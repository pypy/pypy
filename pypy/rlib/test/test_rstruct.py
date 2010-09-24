
from pypy.rpython.test.tool import BaseRtypingTest, LLRtypeMixin, OORtypeMixin
from pypy.rlib.rstruct.runpack import runpack
from pypy.rlib.rstruct import ieee
from pypy.rlib.rarithmetic import LONG_BIT
from pypy.translator.c.test.test_genc import compile
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

class TestCompiled:
    def test_pack_float(self):
        def pack(x):
            result = []
            ieee.pack_float(result, x, 8, False)
            return ''.join(result)
        c_pack = compile(pack, [float])
        def unpack(s):
            return ieee.unpack_float(s, False)
        c_unpack = compile(unpack, [str])

        s = c_pack(123.456)
        assert s == pack(123.456)
        assert c_unpack(s) == 123.456

        s = c_pack(-123.456)
        assert s == pack(-123.456)
        assert c_unpack(s) == -123.456
