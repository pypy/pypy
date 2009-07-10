
import py
from pypy.jit.metainterp.test.test_tl import ToyLanguageTests
from pypy.jit.backend.x86.test.test_zrpy_slist import Jit386Mixin
from pypy.jit.tl import tlc

class TestTL(Jit386Mixin, ToyLanguageTests):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_tl.py
    pass

class TestTLC(Jit386Mixin):
    def _get_interp(self, bytecode_, pool_):
        def interp(inputarg):
            bytecode, pool = tlc.non_constant(bytecode_, pool_)
            args = [tlc.IntObj(inputarg)]
            obj = tlc.interp_eval(bytecode, 0, args, pool)
            return obj.int_o()
        return interp

    def exec_code(self, src, inputarg):
        pool = tlc.ConstantPool()
        bytecode = tlc.compile(src, pool)
        interp = self._get_interp(bytecode, pool)
        return self.meta_interp(interp, [inputarg], view=False)

    def test_fib(self):
        path = py.path.local(tlc.__file__).dirpath('fibo.tlc.src')
        code = path.read()
        res = self.exec_code(code, 20)
        assert res == 6765
