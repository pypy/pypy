from pypy.conftest import gettestobjspace

class AppTestNumPyModule:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_numpy'])

    def test_mean(self):
        from numpy import array, mean
        assert mean(array(range(5))) == 2.0
        assert mean(range(5)) == 2.0

    def test_average(self):
        from numpy import array, average
        assert average(range(10)) == 4.5
        assert average(array(range(10))) == 4.5

    def w_array_compare(self, have, want):
        assert len(have) == len(want)
        mismatch = []
        for num, (x, y) in enumerate(zip(have, want)):
            if not x == y:
                mismatch.append(num)
        if mismatch:
            print have
            print want
            print mismatch
        assert mismatch == []

    def test_bincount_simple(self):
        from numpy import array, bincount
        a = array(range(10))
        have, want = (bincount(a), array([1] * 10))
        self.array_compare(have, want)
        b = array([9, 9, 9, 9, 9])
        have, want = (bincount(b), array([0] * 9 + [5]))
        self.array_compare(have, want)
        c = [9, 9, 9, 9, 9]
        have, want = (bincount(c), array([0] * 9 + [5]))
        self.array_compare(have, want)

    def test_bincount_weights(self):
        from numpy import array, bincount
        a = array([1, 2, 3, 3, 4, 5])
        wa = array([-1, 0.1, 0.2, 0.3, 1, 1])
        have, want = (bincount(a, wa), array([0, -1, 0.1, 0.5, 1, 1]))
        self.array_compare(have, want)
        b = [1, 1, 4]
        wb = [99, -9, 0]
        have, want = (bincount(b, wb), array([0, 90, 0, 0, 0]))
        self.array_compare(have, want)
        c = [1, 1, 1]
        wc = [9, 8, 7]
        have, want = (bincount(c, wc, 4), array([0, 24, 0, 0]))
        self.array_compare(have, want)

    def test_array_compare(self):
        # just some sanity-checks for the comparison function
        from numpy import array
        a = array([1, 2, 4])
        b = array([1, 1, 1])
        raises(AssertionError, "self.array_compare(a, b)")
        x = array([1, 1, 4])
        y = array([1, 1])
        raises(AssertionError, "self.array_compare(x, y)")

    def test_bincount_error_handling(self):
        from numpy import array, bincount
        a = array([1.0, 2.0, 3.0], float)
        raises(TypeError, "bincount(a)")
        b = array([-1, -2, -3])
        raises(ValueError, "bincount(b)")
        c = array([0, 1, 2])
        w = array([1, 2])
        raises(ValueError, "bincount(c, w)")
        raises(ValueError, "bincount([])")

