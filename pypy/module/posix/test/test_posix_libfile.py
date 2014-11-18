import os

from rpython.tool.udir import udir


def setup_module(mod):
    mod.path = udir.join('test_posix_libfile.txt')
    mod.path.write("this is a test")


class AppTestPosix:
    spaceconfig = {
        "usemodules": ['posix', 'time'],
    }

    def setup_class(cls):
        cls.w_posix = cls.space.appexec([], """():
            import %s as m ; return m""" % os.name)
        cls.w_path = cls.space.wrap(str(path))

    def test_posix_is_pypy_s(self):
        assert hasattr(self.posix, '_statfields')

    def test_fdopen(self):
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_RDONLY, 0777)
        f = posix.fdopen(fd, "r")
        result = f.read()
        assert result == "this is a test"

    def test_popen(self):
        import sys
        if sys.platform.startswith('win'):
            skip("unix specific")
        path2 = self.path + '2'
        posix = self.posix

        f = posix.popen("echo hello")
        data = f.read()
        f.close()
        assert data == 'hello\n'

        f = posix.popen("cat > '%s'" % (path2,), 'w')
        f.write('123\n')
        f.close()
        f = open(path2, 'r')
        data = f.read()
        f.close()
        assert data == '123\n'

        import time
        start_time = time.time()
        f = posix.popen("sleep 2")
        f.close()   # should wait here
        end_time = time.time()
        assert end_time - start_time >= 1.9

    def test_popen_and_rebind_file_in___builtin__(self):
        import sys
        if sys.platform.startswith('win'):
            skip("unix specific")
        #
        import __builtin__
        posix = self.posix
        orig_file = file
        try:
            f = posix.popen('true')
            __builtin__.file = lambda x : explode
            f.close()
        finally:
            __builtin__.file = orig_file
