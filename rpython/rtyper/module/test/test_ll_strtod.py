import py

from rpython.rtyper.test.tool import BaseRtypingTest
from rpython.rlib import rfloat

class TestStrtod(BaseRtypingTest):
    def test_formatd(self):
        for flags in [0,
                      rfloat.DTSF_ADD_DOT_0]:
            def f(y):
                return rfloat.formatd(y, 'g', 2, flags)

            assert self.ll_to_string(self.interpret(f, [3.0])) == f(3.0)
