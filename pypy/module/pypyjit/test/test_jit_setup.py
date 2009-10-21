from pypy.conftest import gettestobjspace

class AppTestPyPyJIT:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('pypyjit',))
        cls.space = space

    def test_setup(self):
        # this just checks that the module is setting up things correctly, and
        # the resulting code makes sense on top of CPython.
        import pypyjit
        pypyjit.set_param(threshold=5, inlining=1)
        pypyjit.set_param("trace_eagerness=3,inlining=0")

        def f(x, y):
            return x*y+1

        assert f(6, 7) == 43

        def gen(x):
            i = 0
            while i < x:
                yield i*i
                i += 1

        assert list(gen(3)) == [0, 1, 4]
