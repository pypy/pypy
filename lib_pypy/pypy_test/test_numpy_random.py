from pypy.conftest import gettestobjspace

class AppTestRandom:
    def setup_class(cls):
        cls.space = gettestobjspace(usemodules=['_numpy'])

    def test_rand_single(self):
        from numpy.random import rand
        from numpy import array, dtype

        single = rand(1)
        assert isinstance(single, array)
        assert single.dtype is dtype(float)
        assert single.shape == (1,)
        assert single[0] >= 0
        assert single[0] < 1

    def test_rand_multiple(self):
        from numpy.random import rand
        from numpy import dtype

        multi = rand(5)

        assert multi.shape == (5,)
        assert min(multi) >= 0
        assert max(multi) < 1
        assert multi.dtype is dtype(float)

    def test_randn_single(self):
        from numpy.random import randn

        single = randn()

        assert isinstance(single, float)

    def test_randn_multiple(self):
        from numpy.random import randn

        multi = randn(6)

        assert multi.shape == (6,)

    def test_state(self):
        from numpy.random import set_state, get_state, randn

        state = get_state()
        number = randn()
        other_number = randn()

        set_state(state)
        assert randn() == number
        assert randn() == other_number

    def test_seed(self):
        from numpy.random import seed, rand

        seed(9001)
        number = rand(1)[0]
        other_number = rand(1)[0]

        seed(9001)
        assert number == rand(1)[0]
        assert other_number == rand(1)[0]
