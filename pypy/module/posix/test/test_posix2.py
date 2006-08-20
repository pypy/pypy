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
        fd3 = 1
        posix.dup2(fd2, fd3)
        assert not posix.isatty(fd3)
        s = posix.read(fd, 1)
        assert s == 't'
        posix.lseek(fd, 5, 0)
        s = posix.read(fd, 1)
        assert s == 'i'
        stat = posix.fstat(fd) 
        assert stat  # XXX
        posix.close(fd2)
        posix.close(fd)

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
        ex(self.posix.lstat, "qweqwehello")
        # how can getcwd() raise? 
        ex(self.posix.dup, UNUSEDFD)
        ex(self.posix.dup2, UNUSEDFD, UNUSEDFD)
        ex(self.posix.unlink, str(UNUSEDFD))
        ex(self.posix.remove, str(UNUSEDFD))
        ex(self.posix.chdir, str(UNUSEDFD))
        ex(self.posix.rmdir, str(UNUSEDFD))        
        ex(self.posix.listdir, str(UNUSEDFD))        
        ex(self.posix.chmod, str(UNUSEDFD), 0777)        

    def test_fdopen(self):
        path = self.path 
        posix = self.posix 
        fd = posix.open(path, posix.O_RDONLY, 0777)
        try:
            f = posix.fdopen(fd, "r")
        except NotImplementedError:
            pass
        else:
            raise "did not raise"

    def test_listdir(self):
        pdir = self.pdir
        posix = self.posix 
        result = posix.listdir(pdir)
        result.sort()
        assert result == ['another_longer_file_name',
                          'file1',
                          'file2']

    def test_strerror(self):
        assert isinstance(self.posix.strerror(0), str)
        assert isinstance(self.posix.strerror(1), str)

    def test_fork(self):
        import os
        if hasattr(__import__(os.name), "fork"):
            os = self.posix
            pid = os.fork()
            if pid == 0:   # child
                os._exit(4)
            pid1, status1 = os.waitpid(pid, 0)
            assert pid1 == pid
            # XXX check status1
        else:
            skip("fork not supported")

    def test_read_write(self):
        path = self.path
        posix = self.posix
        fd = posix.open(path, posix.O_WRONLY)
        posix.write(fd, "\nfoo")
        posix.close(fd)
        fd = posix.open(path, posix.O_RDONLY)
        raises(OSError, posix.write, fd, "foo")
        buf = []
        buf.append(posix.read(fd, 4))
        assert len(buf[0]) == 4
        buf.append(posix.read(fd, 255))
        assert "".join(buf) == "\nfoo is a test"
        posix.close(fd)
    
    def test_unlink(self):
        import os
        posix = self.posix
        path = "foo"
        fd = posix.open(path, posix.O_WRONLY | posix.O_CREAT)
        assert os.path.exists(path)
        try:
            posix.unlink(path)
        except OSError:
            print "can't delete '%s'" % path
        else:
            assert not os.path.exists(path)
        posix.close(fd)
    test_remove = test_unlink
    
    def test_getcwd_chdir(self):
        import os
        posix = self.posix
        path = os.path.split(posix.getcwd())[1]
        posix.chdir('..')
        posix.chdir(path)
        posix.getcwd()
        
    def test_mkdir_rmdir(self):
        import os
        posix = self.posix
        path = 'foo'
        try:
            posix.mkdir(path)
        except OSError:
            print "cannot create '%s' directory" % path
        else:
            assert os.path.exists(path)
        try:
            posix.rmdir(path)
        except OSError:
            print "cannot remove '%s' directory" % path
        else:
            assert not os.path.exists(path)
    
    def test_pipe(self):
        posix = self.posix
        r, w = posix.pipe()
        data = 'foobar'
        amount = posix.write(w, data)
        posix.close(w)
        read_data = posix.read(r, amount)
        posix.close(r)
        assert read_data == data
    
    def test_rename(self):
        path = self.path
        posix = self.posix
        new_path = "foo"
        posix.rename(path, new_path)
        posix.rename(new_path, path)
    
    def test_ftruncate(self):
        import os
        pdir = self.pdir
        posix = self.posix
        path = os.path.join(pdir, 'file1')
        fd = posix.open(path, posix.O_WRONLY)
        posix.ftruncate(fd, 2)
        assert posix.stat(path)[6] == 2
        posix.close(fd)
        raises(IOError, posix.ftruncate, 123123, 1)

        
class AppTestEnvironment(object):
    def setup_class(cls): 
        cls.space = space 
        cls.w_posix = space.appexec([], "(): import %s as m ; return m" % os.name)
        cls.w_os = space.appexec([], "(): import os; return os")
        cls.w_path = space.wrap(str(path))

    def test_environ(self):
        posix = self.posix
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
