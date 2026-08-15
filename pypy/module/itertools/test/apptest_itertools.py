import pytest

from itertools import pairwise, count, islice, tee

def test_pairwise():
    assert list(pairwise([])) == []
    assert list(pairwise([1])) == []
    assert list(pairwise([1, 2])) == [(1, 2)]
    assert list(pairwise([1, 2, 3])) == [(1, 2), (2, 3)]

def test_posonly():
    with pytest.raises(TypeError):
        pairwise(iterable='abc')

def test_pairwise_reenter():
    def check(reenter_at, expected):
        class I:
            count = 0
            def __iter__(self):
                return self
            def __next__(self):
                self.count += 1
                if self.count in reenter_at:
                    return next(it)
                return [self.count]  # new object

        it = pairwise(I())
        for item in expected:
            assert next(it) == item

    check({1}, [
        (([2], [3]), [4]),
        ([4], [5]),
    ])
    check({2}, [
        ([1], ([1], [3])),
        (([1], [3]), [4]),
        ([4], [5]),
    ])
    check({3}, [
        ([1], [2]),
        ([2], ([2], [4])),
        (([2], [4]), [5]),
        ([5], [6]),
    ])
    check({1, 2}, [
        ((([3], [4]), [5]), [6]),
        ([6], [7]),
    ])
    check({1, 3}, [
        (([2], ([2], [4])), [5]),
        ([5], [6]),
    ])
    check({1, 4}, [
        (([2], [3]), (([2], [3]), [5])),
        ((([2], [3]), [5]), [6]),
        ([6], [7]),
    ])
    check({2, 3}, [
        ([1], ([1], ([1], [4]))),
        (([1], ([1], [4])), [5]),
        ([5], [6]),
    ])

def test_count_complex():
    assert list(islice(count(3.25-4j), 3)) == [3.25-4j, 4.25-4j, 5.25-4j]

def test_tee_same():
    # issue 5563: change returned values. Fails on CPython3.11
    [a] = tee("xyz", 1)
    b, c = tee(a)
    import sys
    assert next(a) == next(b) == next(c) == "x" 

def test_tee():
    it1, it2 = tee([])
    raises(StopIteration, next, it1)
    raises(StopIteration, next, it2)

    it1, it2 = tee([1, 2, 3])
    for x in [1, 2]:
        assert next(it1) == x
    for x in [1, 2, 3]:
        assert next(it2) == x
    assert next(it1) == 3
    raises(StopIteration, next, it1)
    raises(StopIteration, next, it2)

    assert tee([], 0) == ()

    iterators = tee([1, 2, 3], 10)
    for it in iterators:
        for x in [1, 2, 3]:
            assert next(it) == x
        raises(StopIteration, next, it)

def test_tee_wrongargs():
    raises(TypeError, tee, 0)
    raises(ValueError, tee, [], -1)
    raises(TypeError, tee, [], None)

def test_tee_instantiate():
    a, b = tee(iter('foobar'))
    c = type(a)(a)
    assert a is not b
    assert a is not c
    assert b is not c
    res = list(a)
    assert res == list('foobar')
    res = list(b)
    assert res == list('foobar')
    res = list(c)
    assert res == list('foobar')

def test_tee_function_uses_copy():
    # issue 5563: change returned values. Fails on CPython3.11
    class MyIterator(object):
        def __iter__(self):
            return self
        def __next__(self):
            raise NotImplementedError
        def __copy__(self):
            return iter('def')
    my = MyIterator()
    a, = tee(my, 1)
    assert a is not my
    a, b = tee(my)
    assert a is not my
    assert b is not my
    assert list(b) == ['d', 'e', 'f']


