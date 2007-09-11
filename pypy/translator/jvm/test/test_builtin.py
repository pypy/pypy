
import py
from pypy.translator.oosupport.test_template.builtin import BaseTestBuiltin, BaseTestTime
from pypy.translator.jvm.test.runtest import JvmTest

class TestJavaBuiltin(JvmTest, BaseTestBuiltin):

    def test_os_open_write(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")

    def test_os_write_magic(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")

    def test_os_read(self):
        py.test.skip("ll_os_open is not currently implemented in the Jvm backed")

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

