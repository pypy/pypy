
import py
py.test.skip("Widening to trash error")
from pypy.jit.backend.x86.test.test_basic import Jit386Mixin
from pypy.jit.metainterp.test.test_tlc import TLCTests
from pypy.jit.tl import tlc

class TestTL(Jit386Mixin, TLCTests):
    # for the individual tests see
    # ====> ../../test/test_tlc.py
    
    def test_accumulator(self):
        path = py.path.local(tlc.__file__).dirpath('accumulator.tlc.src')
        code = path.read()
        res = self.exec_code(code, 20)
        assert res == sum(range(20))
        res = self.exec_code(code, -10)
        assert res == 10

    def test_fib(self):
        path = py.path.local(tlc.__file__).dirpath('fibo.tlc.src')
        code = path.read()
        res = self.exec_code(code, 7)
        assert res == 13
        res = self.exec_code(code, 20)
        assert res == 6765
