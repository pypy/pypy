from pypy.conftest import gettestobjspace
import py
import errno
def setup_module(mod): 
    mod.space = gettestobjspace(usemodules=['errno'])

class AppTestErrno: 
    def setup_class(cls): 
        cls.space = space 
        cls.w_errno = space.appexec([], "(): import errno ; return errno")
        cls.w_errorcode = space.wrap(errno.errorcode)

    def test_posix(self):
        assert self.errno.__file__

    def test_constants(self):
        for code, name in self.errorcode.iteritems():
            assert getattr(self.errno, name) == code

    def test_errorcode(self):
        assert self.errorcode == self.errno.errorcode
