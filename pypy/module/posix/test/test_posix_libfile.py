from pypy.conftest import gettestobjspace
from pypy.tool.udir import udir
import os

def setup_module(mod): 
    mod.space = gettestobjspace(usemodules=['posix'], uselibfile=True)
    mod.path = udir.join('posixtestfile.txt') 
    mod.path.write("this is a test")

class AppTestPosix: 
    def setup_class(cls): 
        cls.space = space 
        cls.w_posix = space.appexec([], "(): import %s as m ; return m" % os.name)
        cls.w_path = space.wrap(str(path))
    
    def test_posix_is_pypy_s(self): 
        assert self.posix.__file__ 

    def test_fdopen(self):
        path = self.path 
        posix = self.posix 
        fd = posix.open(path, posix.O_RDONLY, 0777)
        f = posix.fdopen(fd, "r")
        result = f.read()
        assert result == "this is a test"
