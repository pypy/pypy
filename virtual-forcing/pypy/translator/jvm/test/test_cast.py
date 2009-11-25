import py
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.translator.oosupport.test_template.cast import BaseTestCast

class TestCast(BaseTestCast, JvmTest):
    def test_cast_primitive(self):
        # genjvm has buggy support for ullong, so the original test
        # doesn't work
        from pypy.rpython.lltypesystem.lltype import cast_primitive, UnsignedLongLong
        def f(x):
            x = cast_primitive(UnsignedLongLong, x)
            return x
        res = self.interpret(f, [14])
        assert res == 14
