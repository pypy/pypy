def test_tee():
    import itertools

    it1, it2 = itertools.tee([])
    raises(StopIteration, it1.next)
    raises(StopIteration, it2.next)

    it1, it2 = itertools.tee([1, 2, 3])
    for x in [1, 2]:
        assert it1.next() == x
    for x in [1, 2, 3]:
        assert it2.next() == x
    assert it1.next() == 3
    raises(StopIteration, it1.next)
    raises(StopIteration, it2.next)

    assert itertools.tee([], 0) == ()

    iterators = itertools.tee([1, 2, 3], 10)
    for it in iterators:
        for x in [1, 2, 3]:
            assert it.next() == x
        raises(StopIteration, it.next)

def test_tee_wrongargs():
    import itertools

    raises(TypeError, itertools.tee, 0)
    raises(ValueError, itertools.tee, [], -1)
    raises(TypeError, itertools.tee, [], None)

def test_tee_instantiate():
    import itertools

    a, b = itertools.tee(iter('foobar'))
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
