from pypy.conftest import gettestobjspace

class AppTestItertools:
    def setup_class(cls):
        cls.space = gettestobjspace()
        cls.w_itertools = cls.space.appexec([], "(): import itertools; return itertools")

    def test_chain(self):
        it = self.itertools.chain([], [1, 2, 3])
        lst = list(it)
        assert lst == [1, 2, 3]

    def test_islice(self):
        import sys
        itertools = self.itertools

        slic = itertools.islice(itertools.count(), 1, 10, sys.maxint)
        assert len(list(slic)) == 1

        if '__pypy__' not in sys.builtin_module_names:
            skip("this takes ages on top of CPython's itertools module")
        slic = itertools.islice(itertools.count(), 1, 10, sys.maxint-20)
        assert len(list(slic)) == 1
