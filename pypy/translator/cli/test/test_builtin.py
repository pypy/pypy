import os
import py
from pypy.tool import udir
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

def skip_os(self):
    py.test.skip("CLI doesn't support the os module, yet")

class TestCliBuiltin(CliTest, BaseTestRbuiltin):
    test_os_getcwd = skip_os
    test_os_dup = skip_os
    test_os_path_exists = skip_os
    test_os_isdir = skip_os
    test_os_read = skip_os

    # the following tests can't be executed with gencli because they
    # returns file descriptors, and cli code is executed in another
    # process. Instead of those, there is a new test that opens and
    # write to a file all in the same process.
    def test_os_write(self):
        pass
    def test_os_write_single_char(self):
        pass
    def test_os_open(self):
        pass

    def test_os_open_write(self):
        py.test.skip("Temporarily disabled")
        tmpdir = str(udir.udir.join("os_write_test"))
        def fn():
            fd = os.open(tmpdir, os.O_WRONLY|os.O_CREAT, 0777)            
            os.write(fd, "hello world")
            os.close(fd)
        self.interpret(fn, [])
        assert file(tmpdir).read() == 'hello world'
