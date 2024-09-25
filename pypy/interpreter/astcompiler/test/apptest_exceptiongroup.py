from pytest import raises

def test_simple():
    try:
        raise TypeError()
    except* TypeError:
        a = 1
    except* ValueError:
        a = 2
    assert a == 1

def test_both_excepts_run():
    l = []
    try:
        raise ExceptionGroup('abc', [ValueError(), TypeError()])
    except* TypeError:
        l.append(1)
    except* ValueError:
        l.append(2)
    print(l)
    assert l == [1, 2]

def raises_one():
    try:
        raise ExceptionGroup('abc', [ValueError(), TypeError()])
    except* TypeError:
        pass

def test_reraise():
    a = 1
    try:
        raises_one()
    except* ValueError:
        a = 0
    assert a == 0 # and in particular, we reach this line

def error_in_handler():
    try:
        raise ExceptionGroup('abc', [ValueError(), TypeError()])
    except* TypeError:
        1 / 0

def test_error_in_exception_handler():
    a = 1
    try:
        error_in_handler()
    except ExceptionGroup as e:
        assert repr(e) == "ExceptionGroup('', [ZeroDivisionError('division by zero'), ExceptionGroup('abc', [ValueError()])])"
        # TODO what's wrong with the context?
        #assert repr(e.exceptions[0].__context__) == "ExceptionGroup('abc', [TypeError()])"
    else:
        assert 0, "an ExceptionGroup should be raised"

def test_name_except_star():
    l = []
    value = ValueError()
    typ = TypeError()
    try:
        raise ExceptionGroup('abc', [value, typ])
    except* TypeError as e1:
        assert e1.exceptions[0] is typ
        l.append(1)
    except* ValueError as e2:
        assert e2.exceptions[0] is value
        l.append(2)
    print(l)
    assert l == [1, 2]
    with raises(UnboundLocalError):
        e1
    with raises(UnboundLocalError):
        e2

def test_try_star_name_raise_in_except_handler():
    l = []
    value = ValueError()
    typ = TypeError()
    try:
        try:
            raise ExceptionGroup('abc', [value, typ])
        except* TypeError as e1:
            1 / 0
    except Exception as e:
        assert "ZeroDivisionError" in repr(e)
    with raises(UnboundLocalError):
        e1


