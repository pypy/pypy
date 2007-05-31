import py
from pypy.tool import udir
from pypy.translator.jvm.test.runtest import JvmTest
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

class TestJavaBuiltin(JvmTest, BaseTestRbuiltin):
    def test_os(self):
        py.test.skip("Jvm os support uncertain")
    
    def test_os_open(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")
        
    def test_os_getcwd(self):
        py.test.skip("ll_os_getcwd is not currently implemented in the Jvm backed")
    
    def test_os_write(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")
    
    def test_os_write_single_char(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")
    
    def test_os_read(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")
    
    def test_os_path_exists(self):
        py.test.skip("ll_os_stat is not currently implemented in the Jvm backed")
    
    def test_os_isdir(self):
        py.test.skip("ll_os_stat is not currently implemented in the Jvm backed")
    
    def test_builtin_math_floor(self):
        py.test.skip("metavm.py needs to be updated to handle this math op; graphless extrernal")
        
    def test_builtin_math_fmod(self):
        py.test.skip("metavm.py needs to be updated to handle this math op; graphless extrernal")
        
    def test_builtin_math_frexp(self):
        py.test.skip("metavm.py needs to be updated to handle this math op; graphless extrernal")
        
    def test_builtin_math_modf(self):
        py.test.skip("metavm.py needs to be updated to handle this math op; graphless extrernal")
        