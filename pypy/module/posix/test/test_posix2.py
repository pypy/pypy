from pypy.objspace.std import StdObjSpace 
from pypy.tool.udir import udir
from pypy.conftest import gettestobjspace
import os

def setup_module(mod): 
    mod.space = gettestobjspace(usemodules=['posix'])
    mod.path = udir.join('posixtestfile.txt') 
    mod.path.write("this is a test")
    pdir = udir.ensure('posixtestdir', dir=True)
    pdir.join('file1').write("test1")
    os.chmod(str(pdir.join('file1')), 0600)
    pdir.join('file2').write("test2")
    pdir.join('another_longer_file_name').write("test3")
    mod.pdir = pdir

class AppTestPosix: 
    def setup_class(cls): 
        cls.space = space 
        cls.w_posix = space.appexec([], "(): import %s as m ; return m" % os.name)
        cls.w_path = space.wrap(str(path))
        cls.w_pdir = space.wrap(str(pdir))
    
    def test_posix_is_pypy_s(self): 
        assert self.posix.__file__ 

    def test_some_posix_basic_operation(self): 
        path = self.path 
        posix = self.posix 
        fd = posix.open(path, posix.O_RDONLY, 0777)
        fd2 = posix.dup(fd)
        assert not posix.isatty(fd2) 
        s = posix.read(fd, 1)
        assert s == 't'
        posix.lseek(fd, 5, 0)
        s = posix.read(fd, 1)
        assert s == 'i'
        stat = posix.fstat(fd) 
        assert stat  # XXX 
        posix.close(fd2)
        posix.close(fd)

    def test_pickle(self):
        import pickle, os
        st = self.posix.stat(os.curdir)
        print type(st).__module__
        s = pickle.dumps(st)
        print repr(s)
        new = pickle.loads(s)
        assert new == st
        assert type(new) is type(st)

    def test_open_exception(self): 
        posix = self.posix
        try: 
            posix.open('qowieuqwoeiu', 0, 0)
        except OSError: 
            pass
        else: 
            assert 0

    def test_functions_raise_error(self): 
        def ex(func, *args):
            try:
                func(*args)
            except OSError: 
                pass
            else:
                raise AssertionError("%s(%s) did not raise" %(
                                     func.__name__, 
                                     ", ".join([str(x) for x in args])))
        UNUSEDFD = 123123
        ex(self.posix.open, "qweqwe", 0, 0)
        ex(self.posix.lseek, UNUSEDFD, 123, 0)
        #apparently not posix-required: ex(self.posix.isatty, UNUSEDFD)
        ex(self.posix.read, UNUSEDFD, 123)
        ex(self.posix.write, UNUSEDFD, "x")
        ex(self.posix.close, UNUSEDFD)
        #UMPF cpython raises IOError ex(self.posix.ftruncate, UNUSEDFD, 123)
        ex(self.posix.fstat, UNUSEDFD)
        ex(self.posix.stat, "qweqwehello")
        # how can getcwd() raise? 
        ex(self.posix.dup, UNUSEDFD)

    def test_fdopen(self):
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_RDONLY, 0777)
        f = posix.fdopen(fd, "r")
        f.close()

    def test_listdir(self):
        pdir = self.pdir
        posix = self.posix 
        result = posix.listdir(pdir)
        result.sort()
        assert result == ['another_longer_file_name',
                          'file1',
                          'file2']


    def test_access(self):
        pdir = self.pdir + '/file1'
        posix = self.posix

        assert posix.access(pdir, posix.R_OK)
        assert posix.access(pdir, posix.W_OK)
        import sys
        if sys.platform != "win32":
            assert not posix.access(pdir, posix.X_OK)


    def test_strerror(self):
        assert isinstance(self.posix.strerror(0), str)
        assert isinstance(self.posix.strerror(1), str)

    if hasattr(__import__(os.name), "fork"):
        def test_fork(self):
            os = self.posix
            pid = os.fork()
            if pid == 0:   # child
                os._exit(4)
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            # XXX check status1
        pass # <- please, inspect.getsource(), don't crash

    if hasattr(__import__(os.name), "execv"):
        def test_execv(self):
            os = self.posix
            if not hasattr(os, "fork"):
                skip("Need fork() to test execv()")
            pid = os.fork()
            if pid == 0:
                os.execv("/usr/bin/env", ["env", "python", "-c", "open('onefile', 'w').write('1')"])
            os.waitpid(pid, 0)
            assert open("onefile").read() == "1"
            os.unlink("onefile")
        
        def test_execv_raising(self):
            os = self.posix
            raises(OSError, 'os.execv("saddsadsadsadsa", ["saddsadsasaddsa"])')

        def test_execv_raising2(self):
            os = self.posix
            def t(n):
                try:
                    os.execv("xxx", n)
                except TypeError,t:
                    assert t.args[0] == "execv() arg 2 must be an iterable of strings"
                else:
                    py.test.fail("didn't raise")
            t(3)
            t([3, "a"])

        def test_execve(self):
            skip("Not implemented")
            os = self.posix
            pid = os.fork()
            if pid == 0:
                os.execve("/usr/bin/env", ["env", "python", "-c", "import os; open('onefile', 'w').write(os.environ['ddd'])"], {'ddd':'xxx'})
            os.waitpid(pid, 0)
            assert open("onefile").read() == "xxx"
            os.unlink("onefile")
        pass # <- please, inspect.getsource(), don't crash

    if hasattr(__import__(os.name), 'popen'):
        def test_popen(self):
            skip("Not implemented")
            os = self.posix
            stream = os.popen('echo 1')
            assert stream.read() == '1\n'

    def test_utime(self):
        os = self.posix
        import os.path
        # XXX utimes & float support
        path = os.path.join(self.pdir, "test_utime.txt")
        fh = open(path, "w")
        fh.write("x")
        fh.close()
        from time import time, sleep
        t0 = time()
        sleep(1)
        os.utime(path, None)
        assert os.stat(path).st_atime > t0
        os.utime(path, (int(t0), int(t0)))
        assert int(os.stat(path).st_atime) == int(t0)

    def test_utime_raises(self):
        os = self.posix
        raises(TypeError, "os.utime('xxx', 3)")
        raises(OSError, "os.utime('somefilewhichihopewouldneverappearhere', None)")

    def test_wifsignaled(self):
        os = self.posix
        assert os.WIFSIGNALED(0) == False
        assert os.WIFSIGNALED(1) == True

class AppTestEnvironment(object):
    def setup_class(cls): 
        cls.space = space 
        cls.w_posix = space.appexec([], "(): import %s as m ; return m" % os.name)
        cls.w_os = space.appexec([], "(): import os; return os")
        cls.w_path = space.wrap(str(path))

    def test_environ(self):
        posix = self.posix
        os = self.os
        assert posix.environ['PATH']
        del posix.environ['PATH']
        def fn(): posix.environ['PATH']
        raises(KeyError, fn)

    if hasattr(__import__(os.name), "unsetenv"):
        def test_unsetenv_nonexisting(self):
            os = self.os
            os.unsetenv("XYZABC") #does not raise
            try:
                os.environ["ABCABC"]
            except KeyError:
                pass
            else:
                raise AssertionError("did not raise KeyError")
            os.environ["ABCABC"] = "1"
            assert os.environ["ABCABC"] == "1"
            os.unsetenv("ABCABC")
            cmd = '''python -c "import os, sys; sys.exit(int('ABCABC' in os.environ))" '''
            res = os.system(cmd)
            assert res == 0
