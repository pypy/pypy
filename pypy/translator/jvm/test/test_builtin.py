import os, stat
import py
from pypy.tool import udir
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

class TestJavaBuiltin(JvmTest, BaseTestRbuiltin):
    def test_os(self):
        py.test.skip("Jvm os support uncertain")
    
    def test_os_open(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")
        
    def test_os_write(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")
    
    def test_os_write_single_char(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")
    
    def test_os_read(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")
    
    def test_os_stat(self):
        def fn(flag):
            if flag:
                return os.stat('.')[0]
            else:
                return os.stat('.').st_mode
        mode = self.interpret(fn, [0])
        assert stat.S_ISDIR(mode)
        mode = self.interpret(fn, [1])
        assert stat.S_ISDIR(mode)

    def test_os_stat_oserror(self):
        def fn():
            return os.stat('/directory/unlikely/to/exists')[0]
        self.interpret_raises(OSError, fn, [])

    def test_builtin_math_frexp(self):
        py.test.skip("metavm.py needs to be updated to handle this math op; graphless extrernal")
        
    def test_builtin_math_modf(self):
        py.test.skip("metavm.py needs to be updated to handle this math op; graphless extrernal")

    def test_os_dup(self):
        py.test.skip("not implemented")
