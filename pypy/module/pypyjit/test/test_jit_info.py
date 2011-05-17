from pypy.conftest import gettestobjspace

class AppTestJitInfo(object):
    def setup_class(cls):
        space = gettestobjspace(usemodules=('pypyjit',))
        cls.space = space

    def test_getjitinfo(self):
        import pypyjit

        def f():
            pass

        pypyjit.getjitinfo(f.func_code)
        # assert did not crash

