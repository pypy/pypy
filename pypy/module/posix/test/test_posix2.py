from pypy.objspace.std import StdObjSpace 
from pypy.tool.udir import udir

def setup_module(mod): 
    mod.space = StdObjSpace(usemodules=['posix'])
    mod.path = udir.join('posixtestfile.txt') 
    mod.path.write("this is a test")

class AppTestPosix: 
    def setup_class(cls): 
        cls.space = space 
        cls.w_posix = space.appexec([], "(): import posix ; return posix")
        cls.w_path = space.wrap(str(path))
    
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
