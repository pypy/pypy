from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestRandom(BaseNumpyAppTest):
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

    def test_randint_single(self):
        from numpy.random import randint

        for i in range(100):
            integer = randint(4)
            assert isinstance(integer, int)
            assert 0 <= integer < 4

        for i in range(100):
            integer = randint(9, 12)
            assert isinstance(integer, int)
            assert 9 <= integer < 12

    def test_randint_multi(self):
        from numpy.random import randint

        integers = randint(4, size=(100,))
        assert integers.shape == (100,)
        for x in integers:
            assert 0 <= x < 4

        integers = randint(9, 12, (100,))
        for x in integers:
            assert 9 <= x < 12

    def test_random_integers_single(self):
        from numpy.random import random_integers

        for i in range(100):
            integer = random_integers(4)
            assert 0 <= integer <= 4

        for i in range(100):
            integer = random_integers(9, 12)
            assert 9 <= integer <= 12

    def test_random_integers_multi(self):
        from numpy.random import random_integers

        integers = random_integers(5, size=(100,))
        assert integers.shape == (100,)
        for x in integers:
            assert 0 <= integers[x] <= 5

        integers = random_integers(9, 12, (100,))
        assert integers.shape == (100,)
        for x in integers:
            assert 9 <= x <= 12
