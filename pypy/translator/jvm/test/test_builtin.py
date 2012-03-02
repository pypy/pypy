
import py
from pypy.translator.oosupport.test_template.builtin import BaseTestBuiltin, BaseTestTime
from pypy.translator.jvm.test.runtest import JvmTest

class TestJavaBuiltin(JvmTest, BaseTestBuiltin):

    def test_os_write_magic(self):
        self._skip_win('os_write_magic not on windows')
        BaseTestBuiltin.test_os_write_magic(self)

    def test_os_path_exists(self):
        py.test.skip("fails in annotation stage, unrelated to JVM I think")
        
    def test_os_isdir(self):
        py.test.skip("fails in annotation stage, unrelated to JVM I think")

    def test_os_dup(self):
        py.test.skip("test N/A to jvm: replaced by test_os_dup_oo")

    def test_environ(self):
        py.test.skip('fixme! how to set environment variables in Java?') 

    def test_os_read_binary_crlf(self):
        py.test.skip('fixme!')

    def test_debug_llinterpcall(self):
        py.test.skip("so far, debug_llinterpcall is only used on lltypesystem")

    def test_os_access(self):
        from socket import gethostname
        if 1:  # gethostname() == 'wyvern':
            py.test.skip('bug in JDK when run headless: ' +
                         'http://bugs.sun.com/bugdatabase/view_bug.do?bug_id=6539705')
        BaseTestBuiltin.test_os_access(self)

    def test_cast_primitive(self):
        py.test.skip('fixme!')

    def test_os_fstat(self):
        import os, stat
        def fn():
            fd = os.open(__file__, os.O_RDONLY, 0)
            st = os.fstat(fd)
            os.close(fd)
            return st.st_mode
        res = self.interpret(fn, [])
        assert stat.S_ISREG(res)

class TestJvmTime(JvmTest, BaseTestTime):

    pass

