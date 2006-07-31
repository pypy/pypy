import platform
import os, stat
import py
from pypy.tool import udir
from pypy.translator.cli.test.runtest import CliTest
from pypy.rpython.test.test_rbuiltin import BaseTestRbuiltin

def skip_os(self):
    py.test.skip("CLI doesn't support the os module, yet")

def skip_win():
    if platform.system() == 'Windows':
        py.test.skip("Doesn't work on Windows, yet")

class TestCliBuiltin(CliTest, BaseTestRbuiltin):
    test_os_dup = skip_os
    test_os_path_exists = skip_os
    test_os_isdir = skip_os

    def test_os_read(self):
        BaseTestRbuiltin.test_os_read(self)

    def test_os_read_binary(self):
        tmpfile = str(udir.udir.join("os_read_test"))
        def fn():
            from pypy.module.__builtin__.importing import BIN_READMASK
            fd = os.open(tmpfile, BIN_READMASK, 0666)
            res = os.read(fd, 4096)
            os.close(fd)
            return len(res)
        f = file(tmpfile, 'w')
        f.write('Hello\nWorld')
        f.close()
        assert self.interpret(fn, []) == len(file(tmpfile, 'rb').read())

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
        tmpdir = str(udir.udir.join("os_write_test"))
        def fn():
            fd = os.open(tmpdir, os.O_WRONLY|os.O_CREAT, 0777)            
            os.write(fd, "hello world")
            os.close(fd)
        self.interpret(fn, [])
        assert file(tmpdir).read() == 'hello world'

    def test_os_stat(self):
        def fn():
            return os.stat('.')[0]
        mode = self.interpret(fn, [])
        assert stat.S_ISDIR(mode)

    def test_os_stat_oserror(self):
        def fn():
            return os.stat('/directory/unlikely/to/exists')[0]
        self.interpret_raises(OSError, fn, [])

    # XXX: remember to test ll_os_readlink and ll_os_pipe as soon as
    # they are implemented
