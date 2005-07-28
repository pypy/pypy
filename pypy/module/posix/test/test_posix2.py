from pypy.objspace.std import StdObjSpace 
from pypy.tool.udir import udir

def setup_module(mod): 
    mod.space = StdObjSpace(usemodules=['posix'])
    mod.path = udir.join('posixtestfile.txt') 
    mod.path.write("this is a test")

class AppTestPosix: 
    def setup_class(cls): 
        cls.space = space 
    
    def test_posix_is_pypy_s(self): 
        import posix
        assert posix.__file__ 

def test_some_posix_basic_operation(): 
    w_path = space.wrap(str(path))
    space.appexec([w_path], """(path):
        import posix
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
    """)
