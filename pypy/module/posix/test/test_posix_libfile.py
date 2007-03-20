from pypy.conftest import gettestobjspace
from pypy.tool.udir import udir
import os

def setup_module(mod):
    mod.space = gettestobjspace(usemodules=['posix'])
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
