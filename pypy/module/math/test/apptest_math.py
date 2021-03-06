import math

def test_product():
    assert math.prod([1, 2, 3]) == 6
    assert math.prod([1, 2, 3], start=0.5) == 3.0
    assert math.prod([]) == 1.0
    assert math.prod([], start=5) == 5

def test_julians_weird_test_prod():
    class A:
        def __mul__(self, other):
                return 12
        def __imul__(self, other):
                return 13

    # check that the implementation doesn't use *=
    assert math.prod([1, 2], start=A())

def test_more_weird_prod():
    start = [4]
    assert math.prod([2], start=start) == [4, 4]
    assert start == [4]
    start =  object()
    assert math.prod([], start=start) is start


def test_comb():
    from math import comb, factorial

    assert comb(10, 11) == 0
    for n in range(5):
        for k in range(n + 1):
            assert comb(n, k) == factorial(n) // (factorial(k) * factorial(n - k))

    class A:
        def __index__(self):
            return 4

    assert comb(A(), 2) == comb(4, 2)


def test_perm():
    from math import perm, factorial

    assert perm(10, 11) == 0

    for n in range(5):
        for k in range(n + 1):
            assert perm(n, k) == factorial(n) // factorial(n - k)

    class A:
        def __index__(self):
            return 4

    assert perm(A(), 2) == perm(4, 2)
