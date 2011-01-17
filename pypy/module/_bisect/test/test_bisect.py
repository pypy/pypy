from pypy.conftest import gettestobjspace


class AppTestBisect:

    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_bisect'])

    def test_bisect_left(self):
        from _bisect import bisect_left
        a = [0, 5, 6, 6, 6, 7]
        assert bisect_left(a, None) == 0
        assert bisect_left(a, -3) == 0
        assert bisect_left(a, 0) == 0
        assert bisect_left(a, 3) == 1
        assert bisect_left(a, 5) == 1
        assert bisect_left(a, 5.5) == 2
        assert bisect_left(a, 6) == 2
        assert bisect_left(a, 6.0) == 2
        assert bisect_left(a, 6.1) == 5
        assert bisect_left(a, 7) == 5
        assert bisect_left(a, 8) == 6
        a = []
        assert bisect_left(a, 123) == 0
        a = [9]
        assert bisect_left(a, -123) == 0
        assert bisect_left(a, 9) == 0
        assert bisect_left(a, 123) == 1
        a = [9, 9]
        assert bisect_left(a, -123) == 0
        assert bisect_left(a, 9) == 0
        assert bisect_left(a, 123) == 2
        a = [4, 6, 6, 9]
        assert bisect_left(a, 6, 0) == 1
        assert bisect_left(a, 6, 1) == 1
        assert bisect_left(a, 6, 2) == 2
        assert bisect_left(a, 6, 3) == 3
        assert bisect_left(a, 6, 4) == 4
        assert bisect_left(a, 6, 0, 0) == 0
        assert bisect_left(a, 6, 0, 1) == 1
        assert bisect_left(a, 6, 0, 2) == 1
        assert bisect_left(a, 6, 0, 3) == 1
        assert bisect_left(a, 6, 0, 4) == 1

        raises(ValueError, bisect_left, [1, 2, 3], 5, -1, 3)

    def test_bisect_right(self):
        from _bisect import bisect_right
        a = [0, 5, 6, 6, 6, 7]
        assert bisect_right(a, None) == 0
        assert bisect_right(a, -3) == 0
        assert bisect_right(a, 0) == 1
        assert bisect_right(a, 3) == 1
        assert bisect_right(a, 5) == 2
        assert bisect_right(a, 5.5) == 2
        assert bisect_right(a, 6) == 5
        assert bisect_right(a, 6.0) == 5
        assert bisect_right(a, 6.1) == 5
        assert bisect_right(a, 7) == 6
        assert bisect_right(a, 8) == 6
        a = []
        assert bisect_right(a, 123) == 0
        a = [9]
        assert bisect_right(a, -123) == 0
        assert bisect_right(a, 9) == 1
        assert bisect_right(a, 123) == 1
        a = [9, 9]
        assert bisect_right(a, -123) == 0
        assert bisect_right(a, 9) == 2
        assert bisect_right(a, 123) == 2
        a = [4, 6, 6, 9]
        assert bisect_right(a, 6, 0) == 3
        assert bisect_right(a, 6, 1) == 3
        assert bisect_right(a, 6, 2) == 3
        assert bisect_right(a, 6, 3) == 3
        assert bisect_right(a, 6, 4) == 4
        assert bisect_right(a, 6, 0, 0) == 0
        assert bisect_right(a, 6, 0, 1) == 1
        assert bisect_right(a, 6, 0, 2) == 2
        assert bisect_right(a, 6, 0, 3) == 3
        assert bisect_right(a, 6, 0, 4) == 3

    def test_insort_left(self):
        from _bisect import insort_left
        a = [0, 5, 6, 6, 6, 7]
        insort_left(a, 6.0)
        assert a == [0, 5, 6.0, 6, 6, 6, 7]
        assert map(type, a) == [int, int, float, int, int, int, int]

    def test_insort_right(self):
        from _bisect import insort_right
        a = [0, 5, 6, 6, 6, 7]
        insort_right(a, 6.0)
        assert a == [0, 5, 6, 6, 6, 6.0, 7]
        assert map(type, a) == [int, int, int, int, int, float, int]
