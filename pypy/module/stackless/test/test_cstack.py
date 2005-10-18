from pypy.conftest import gettestobjspace


class AppTestCStack:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('stackless',))
        cls.space = space

    def test_dummy(self):
        # dummy tests, mostly just testing that they don't crash
        import stackless
        stackless.cstack_unwind()
        assert not stackless.cstack_too_big()
        stackless.cstack_check()

    def test_frames_depth(self):
        import stackless
        def f(n):
            if n == 0:
                return []
            lst = f(n-1)
            lst.append(stackless.cstack_frames_depth())
            return lst
        lst = f(5)
        assert lst[0] > lst[1] > lst[2] > lst[3] > lst[4] > 0
