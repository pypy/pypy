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

def test_batched():
    from itertools import batched
    assert list(batched('ABCDEFG', 3)) == [
        ('A', 'B', 'C'), ('D', 'E', 'F'), ('G',)]
    assert list(batched('ABCDEF', 3)) == [('A', 'B', 'C'), ('D', 'E', 'F')]
    assert list(batched('', 3)) == []
    # n as keyword
    assert list(batched('ABCD', n=2)) == [('A', 'B'), ('C', 'D')]
    # n must be at least one
    with pytest.raises(ValueError):
        list(batched('ABC', 0))
    with pytest.raises(ValueError):
        list(batched('ABC', -1))
    # exhausted iterator stays exhausted
    it = batched('AB', 5)
    assert next(it) == ('A', 'B')
    with pytest.raises(StopIteration):
        next(it)
    with pytest.raises(StopIteration):
        next(it)

def test_tee_of_tee_independent():
    # gh-123884 / pypy #5284: tee() of a tee'd iterator must produce
    # independent iterators sharing the buffer, not the input itself.
    from itertools import tee
    def consume(it, up_to):
        i = 0
        while i < up_to:
            try:
                next(it)
            except StopIteration:
                break
            i += 1
        return i
    [my_iter] = tee(iter(range(100)), 1)
    [preview] = tee(my_iter, 1)
    assert preview is not my_iter
    assert consume(preview, 5) == 5
    assert consume(my_iter, 100) == 100

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

def test_tee_function_ignores_copy():
    # issue 5563: none of the results is the input
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
    with pytest.raises(NotImplementedError):
        next(b)

def test_zip_longest_exhausted_twice():
    # list() twice on a zip_longest whose first sub-iterator was
    # exhausted (and replaced by None internally) segfaulted
    from itertools import zip_longest
    z = zip_longest([1, 2, 3], range(5))
    assert list(z) == [(1, 0), (2, 1), (3, 2), (None, 3), (None, 4)]
    assert list(z) == []
    assert sorted(z) == []
    z = zip_longest([1], range(3), range(4))
    list(z)
    assert set(z) == set()

def test_islice_checks_args_before_iter():
    class NoneIter:
        def __iter__(self):
            return None
    with pytest.raises(ValueError):
        islice(NoneIter(), "x")
    with pytest.raises(ValueError):
        islice(NoneIter(), -1)
    with pytest.raises(ValueError):
        islice(NoneIter(), 0, 1, 0)

def test_tee_calls_iter_on_iterator():
    class Iterator:
        def __iter__(self):
            return None
        def __next__(self):
            raise StopIteration
    class Iterable:
        def __iter__(self):
            return Iterator()
    with pytest.raises(TypeError):
        tee(Iterable())
    with pytest.raises(TypeError):
        tee(Iterable(), 1)
    Iterator.__copy__ = lambda self: iter('x')
    with pytest.raises(TypeError):
        tee(Iterable())

def test_tee_zero_does_not_call_iter():
    class NoneIter:
        def __iter__(self):
            return None
    assert tee(NoneIter(), 0) == ()
