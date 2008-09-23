import py
py.test.skip("JIT disabled for now")
from pypy.conftest import gettestobjspace

class AppTestPyPyJIT:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('pypyjit',))
        cls.space = space

    def test_setup(self):
        # this just checks that the module is setting up things correctly, and
        # the resulting code makes sense on top of CPython.
        import pypyjit

        def f(x, y):
            return x*y+1

        assert f(6, 7) == 43
        pypyjit.enable(f.func_code)
        assert f(6, 7) == 43

        def gen(x):
            i = 0
            while i < x:
                yield i*i
                i += 1

        assert list(gen(3)) == [0, 1, 4]
        pypyjit.enable(gen.func_code)
        assert list(gen(3)) == [0, 1, 4]
