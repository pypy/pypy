from pypy.conftest import gettestobjspace

class AppTestPwd:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['pwd'])

    def test_getpwuid(self):
        import pwd
        raises(KeyError, pwd.getpwuid, -1)
        pw = pwd.getpwuid(0)
        assert pw.pw_name == 'root'
        assert isinstance(pw.pw_passwd, str)
        assert pw.pw_uid == 0
        assert pw.pw_gid == 0
        assert pw.pw_dir == '/root'
        assert pw.pw_shell.startswith('/')

    def test_getpwnam(self):
        import pwd
        raises(KeyError, pwd.getpwnam, '~invalid~')
        assert pwd.getpwnam('root').pw_name == 'root'

    def test_getpwall(self):
        import pwd
        assert pwd.getpwnam('root') in pwd.getpwall()
