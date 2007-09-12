
import py
from pypy.translator.oosupport.test_template.builtin import BaseTestBuiltin, BaseTestTime
from pypy.translator.jvm.test.runtest import JvmTest

def skip_win():
    import platform
    if platform.system() == 'Windows':
        py.test.skip("Doesn't work on Windows, yet")

class TestJavaBuiltin(JvmTest, BaseTestBuiltin):

    def test_os_write_magic(self):
        skip_win()
        BaseTestBuiltin.test_os_write_magic(self)

    def test_builtin_math_frexp(self):
        py.test.skip("metavm.py needs to be updated to handle this math op; graphless extrernal")
        
    def test_builtin_math_modf(self):
        py.test.skip("metavm.py needs to be updated to handle this math op; graphless extrernal")

    def test_os_dup(self):
        py.test.skip("not implemented")

    def test_environ_items(self):
        py.test.skip('fixme!')

    def test_environ(self):
        py.test.skip('fixme!')

    def test_os_listdir(self):
        py.test.skip('fixme!')

    def test_os_read_binary_crlf(self):
        py.test.skip('fixme!')

    

class TestJvmTime(JvmTest, BaseTestTime):

    def test_time_sleep(self):
        py.test.skip('fixme!')

