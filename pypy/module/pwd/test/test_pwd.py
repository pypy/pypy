import os
import py

if os.name != 'posix':
    py.test.skip('pwd module only available on unix')

class AppTestPwd:
    spaceconfig = dict(usemodules=['pwd'])

    def test_getpwuid(self):
        import pwd, sys
        raises(KeyError, pwd.getpwuid, -1)
        pw = pwd.getpwuid(0)
        assert pw.pw_name == 'root'
        assert isinstance(pw.pw_passwd, str)
        assert pw.pw_uid == 0
        assert pw.pw_gid == 0
        if sys.platform.startswith('linux'):
            assert pw.pw_dir == '/root'
        else:
            assert pw.pw_dir.startswith('/')
        assert pw.pw_shell.startswith('/')
        assert type(pw.pw_uid) is int
        assert type(pw.pw_gid) is int
        # should be out of uid_t range
        raises(TypeError, pwd.getpwuid)
        raises(TypeError, pwd.getpwuid, 3.14)
        raises(KeyError, pwd.getpwuid, sys.maxint)
        raises(KeyError, pwd.getpwuid, -1)
        raises(KeyError, pwd.getpwuid, 2**128)
        raises(KeyError, pwd.getpwuid, -2**128)

    def test_getpwnam(self):
        import pwd
        raises(TypeError, pwd.getpwnam)
        raises(TypeError, pwd.getpwnam, 42)
        raises(KeyError, pwd.getpwnam, '~invalid~')
        assert pwd.getpwnam('root').pw_name == 'root'

    def test_getpwall(self):
        import pwd
        raises(TypeError, pwd.getpwall, 42)
        assert pwd.getpwnam('root') in pwd.getpwall()
