import pytest


def test_is_integer():
    for x in (0, 1, -1, 42, -2**100, 2**100, True, False):
        assert x.is_integer() is True


def test_hash():
    assert hash(-1) == (-1).__hash__() == -2
    assert hash(-2) == (-2).__hash__() == -2


def test_conjugate():
    assert (1).conjugate() == 1
    assert (-1).conjugate() == -1

    class I(int):
        pass
    assert I(1).conjugate() == 1

    class I(int):
        def __pos__(self):
            return 42
    assert I(1).conjugate() == 1


def test_trunc():
    import math
    assert math.trunc(1) == 1
    assert math.trunc(-1) == -1


def test_int_callable():
    assert 43 == int(43)


def test_numerator_denominator():
    assert (1).numerator == 1
    assert (1).denominator == 1
    assert (42).numerator == 42
    assert (42).denominator == 1


def test_int_string():
    assert 42 == int("42")
    assert 10000000000 == int("10000000000")


def test_int_no_whitespace_after_sign():
    pytest.raises(ValueError, int, '+ 42')
    pytest.raises(ValueError, int, '- 42')


def test_int_string_limit():
    import sys
    max_str_digits = sys.get_int_max_str_digits()
    pytest.raises(ValueError, int, '1' * (max_str_digits + 1))
    # should not fail
    x = int(' ' + '1' * max_str_digits)
    sys.set_int_max_str_digits(0)
    try:
        x = int('1' * (max_str_digits + 1))
    finally:
        sys.set_int_max_str_digits(max_str_digits)


def test_int_float():
    assert 4 == int(4.2)


def test_int_str_repr():
    assert "42" == str(42)
    assert "42" == repr(42)
    pytest.raises(ValueError, int, '0x2A')


def test_int_two_param():
    assert 42 == int('0x2A', 0)
    assert 42 == int('2A', 16)
    assert 42 == int('42', 10)
    pytest.raises(TypeError, int, 1, 10)
    pytest.raises(TypeError, int, '5', '9')


def test_int_largenums():
    import sys
    for x in [-sys.maxsize-1, -1, sys.maxsize]:
        y = int(str(x))
        assert y == x
        assert type(y) is int


def test_int_w_long_arg():
    assert int(10000000000) == 10000000000
    assert int("10000000000") == 10000000000
    pytest.raises(ValueError, int, "10000000000JUNK")
    pytest.raises(ValueError, int, "10000000000JUNK", 10)


def test_int_subclass_ctr():
    import sys
    class j(int):
        pass
    assert j(100) == 100
    assert isinstance(j(100),j)
    assert j(100) == 100
    assert j("100") == 100
    assert j("100",2) == 4
    assert isinstance(j("100",2),j)


def test_int_subclass_int():
    class j(int):
        def __int__(self):
            return value
        def __repr__(self):
            return '<instance of j>'
    class subint(int):
        pass
    value = 42
    assert int(j()) == 42
    value = 4200000000000000000000000000000000
    assert int(j()) == 4200000000000000000000000000000000
    value = subint(42)
    assert int(j()) == 42 and type(int(j())) is int
    value = subint(4200000000000000000000000000000000)
    assert (int(j()) == 4200000000000000000000000000000000
            and type(int(j())) is int)
    value = 42.0
    pytest.raises(TypeError, int, j())
    value = "foo"
    pytest.raises(TypeError, int, j())


def test_special_int():
    class a(object):
        def __int__(self):
            self.ar = True
            return None
    inst = a()
    pytest.raises(TypeError, int, inst)
    assert inst.ar == True

    class b(object):
        pass
    pytest.raises((AttributeError, TypeError), int, b())


def test_special_long():
    class a(object):
        def __int__(self):
            self.ar = True
            return None
    inst = a()
    pytest.raises(TypeError, int, inst)
    assert inst.ar == True

    class b(object):
        pass
    pytest.raises((AttributeError, TypeError), int, b())


def test_just_trunc():
    import warnings
    class myint(object):
        def __trunc__(self):
            return 42
    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter("always", DeprecationWarning)
        assert int(myint()) == 42
        assert log[0].category == DeprecationWarning


def test_override___int__():
    class myint(int):
        def __int__(self):
            return 42
    assert int(myint(21)) == 42
    class myotherint(int):
        pass
    assert int(myotherint(21)) == 21


def test_trunc_returns_non_int():
    import warnings
    class Integral(object):
        def __int__(self):
            return 42
    class TruncReturnsNonInt(object):
        def __trunc__(self):
            return Integral()
    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter("always", DeprecationWarning)
        with pytest.raises(TypeError):
            int(TruncReturnsNonInt())
        assert log[0].category == DeprecationWarning


def test_trunc_returns_int_subclass():
    import warnings
    class TruncReturnsNonInt:
        def __trunc__(self):
            return True
    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter("always", DeprecationWarning)
        n = int(TruncReturnsNonInt())
        assert log[0].category == DeprecationWarning
    assert n == 1
    assert type(n) is int


def test_trunc_returns_int_subclass_2():
    import warnings
    class BadInt:
        def __int__(self):
            return True
    class TruncReturnsBadInt:
        def __trunc__(self):
            return BadInt()
    bad_int = TruncReturnsBadInt()
    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter("always", DeprecationWarning)
        with pytest.raises(TypeError):
            int(bad_int)
        assert log[0].category == DeprecationWarning


def test_trunc_returns_index():
    import warnings
    class Index:
        def __index__(self):
            return 17
    class TruncReturnsIndex:
        def __trunc__(self):
            return Index()
    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter("always", DeprecationWarning)
        assert int(TruncReturnsIndex()) == 17
        assert log[0].category == DeprecationWarning


def test_int_before_string():
    class Integral(str):
        def __int__(self):
            return 42
    assert int(Integral('abc')) == 42


def test_getnewargs():
    assert  0 .__getnewargs__() == (0,)


def test_bit_length():
    for val, bits in [
        (0, 0),
        (1, 1),
        (10, 4),
        (150, 8),
        (-1, 1),
        (-2, 2),
        (-3, 2),
        (-4, 3),
        (-10, 4),
        (-150, 8),
    ]:
        assert val.bit_length() == bits


def test_bit_length_max():
    import sys
    val = -sys.maxsize-1
    bits = 32 if val == -2147483648 else 64
    assert val.bit_length() == bits


def test_int_real():
    class A(int): pass
    b = A(5).real
    assert type(b) is int


def test_int_error_msg():
    e = pytest.raises(TypeError, int, [])
    assert str(e.value) == ("int() argument must be a string, a bytes-"
                            "like object or a real number, not 'list'")


def test_invalid_literal_message():
    import sys
    if '__pypy__' not in sys.builtin_module_names:
        pytest.skip('PyPy 2.x/CPython 3.4 only')
    for value in b'  1j ', '  1٢٣٤j ':
        try:
            int(value)
        except ValueError as e:
            assert repr(value) in str(e)
        else:
            assert False, value


def test_int_error_msg_surrogate():
    value = u'123\ud800'
    e = pytest.raises(ValueError, int, value)
    assert str(e.value) == u"invalid literal for int() with base 10: %r" % value
    e = pytest.raises(ValueError, int, value, 10)
    assert str(e.value) == u"invalid literal for int() with base 10: %r" % value


def test_non_numeric_input_types():
    # Test possible non-numeric types for the argument x, including
    # subclasses of the explicitly documented accepted types.
    class CustomStr(str): pass
    class CustomBytes(bytes): pass
    class CustomByteArray(bytearray): pass

    factories = [
        bytes,
        bytearray,
        lambda b: CustomStr(b.decode()),
        CustomBytes,
        CustomByteArray,
        memoryview,
    ]
    try:
        from array import array
    except ImportError:
        pass
    else:
        factories.append(lambda b: array('B', b))

    for f in factories:
        x = f(b'100')
        assert int(x) == 100
        if isinstance(x, (str, bytes, bytearray)):
            assert int(x, 2) == 4
        else:
            try:
                int(x, 2)
            except TypeError as e:
                assert "can't convert non-string" in str(e)
            else:
                assert False, 'did not raise'
        try:
            int(f(b'A' * 0x10))
        except ValueError as e:
            assert "invalid literal" in str(e)
        else:
            assert False, 'did not raise'


def test_fake_int_as_base():
    class MyInt(object):
        def __init__(self, x):
            self.x = x
        def __index__(self):
            return self.x

    base = MyInt(24)
    assert int('10', base) == 24

    class MyNonIndexable(object):
        def __init__(self, x):
            self.x = x
        def __int__(self):
            return self.x

    base = MyNonIndexable(24)
    e = pytest.raises(TypeError, int, '10', base)
    assert str(e.value) == ("'MyNonIndexable' object cannot be interpreted "
                            "as an integer")


def test_int_of_bool():
    x = int(False)
    assert x == 0
    assert type(x) is int
    assert str(x) == "0"


def test_ceil():
    assert 8 .__ceil__() == 8


def test_floor():
    assert 8 .__floor__() == 8


def test_deprecation_warning_1():
    import warnings, _operator
    class BadInt:
        def __int__(self):
            return True
        def __index__(self):
            return False
    bad = BadInt()
    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter("always", DeprecationWarning)
        n = int(bad)
        m = _operator.index(bad)
    assert n == 1 and type(n) is int
    assert m == 0 and type(m) is int
    assert len(log) == 2


def test_deprecation_warning_2():
    import warnings, _operator
    class BadInt(int):
        def __int__(self):
            return self
        def __index__(self):
            return self
    bad = BadInt(1)
    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter("always", DeprecationWarning)
        n = int(bad)
        m = _operator.index(bad)  # no warning
    assert n == 1 and type(n) is int
    assert m == 1 and type(m) is int
    assert len(log) == 1
    assert log[0].message.args[0].startswith('__int__')


def test_deprecation_warning_3():
    import warnings, _operator
    class BadInt(int):
        def __int__(self):
            return self
        def __index__(self):
            return self
    bad = BadInt(2**100)
    with warnings.catch_warnings(record=True) as log:
        warnings.simplefilter("always", DeprecationWarning)
        n = int(bad)
        m = _operator.index(bad)  # no warning
    assert n == bad and type(n) is int
    assert m == bad and type(m) is int
    assert len(log) == 1
    assert log[0].message.args[0].startswith('__int__')


def test_int_nonstr_with_base():
    assert int(b'100', 2) == 4
    assert int(bytearray(b'100'), 2) == 4
    pytest.raises(TypeError, int, memoryview(b'100'), 2)


def test_from_bytes():
    called = []
    class X(int):
        def __init__(self, val):
            called.append(val)
    x = X.from_bytes(b"", 'little')
    assert type(x) is X and x == 0
    assert called == [0]
    x = X.from_bytes(b"*" * 100, 'little')
    assert type(x) is X
    expected = sum(256 ** i for i in range(100)) * ord('*')
    assert x == expected
    assert called == [0, expected]


def test_from_to_bytes_text_signature():
    assert int.from_bytes.__text_signature__ == "($type, /, bytes, byteorder='big', *, signed=False)"
    assert int.to_bytes.__text_signature__ == "($self, /, length=1, byteorder='big', *, signed=False)"


def test_leading_zero_literal():
    assert eval("00") == 0
    pytest.raises(SyntaxError, eval, '07')
    assert int("00", 0) == 0
    pytest.raises(ValueError, int, '07', 0)
    assert int("07", 10) == 7
    pytest.raises(ValueError, int, '07777777777777777777777777777777777777', 0)
    pytest.raises(ValueError, int, '00000000000000000000000000000000000007', 0)
    pytest.raises(ValueError, int, '00000000000000000077777777777777777777', 0)


def test_round_special_method():
    assert 567 .__round__(-1) == 570
    assert 567 .__round__() == 567
    import sys
    if '__pypy__' in sys.builtin_module_names:
        assert 567 .__round__(None) == 567    # fails on CPython


def test_error_message_wrong_self():
    import sys
    unboundmeth = int.__str__
    if '__pypy__' in sys.builtin_module_names:
        # PyPy type-checks 'self' here; CPython's int.__str__ has no
        # own tp_str and falls back to a generic path with no check,
        # so int.__str__("!") just returns "!" there.
        e = pytest.raises(TypeError, unboundmeth, "!")
        assert "int" in str(e.value)
        if hasattr(unboundmeth, 'im_func'):
            e = pytest.raises(TypeError, unboundmeth.im_func, "!")
            assert "'int'" in str(e.value)
    else:
        assert unboundmeth("!") == "'!'"


def test_int_new_pos_only():
    import sys
    with pytest.raises(TypeError) as info:
        int(x=1)
    if '__pypy__' in sys.builtin_module_names:
        # PyPy's generic positional-only-argument error wording differs
        # from CPython's here.
        assert "got some positional-only arguments passed as keyword arguments: 'x'" in str(info.value)
    else:
        assert "'x' is an invalid keyword argument for int()" in str(info.value)


def test_int_as_integer_ratio():
    assert 4 .as_integer_ratio() == (4, 1)
    assert (-1).as_integer_ratio() == (-1, 1)
    assert (2 ** 100).as_integer_ratio() == (2 ** 100).as_integer_ratio()

    d, n = True.as_integer_ratio()
    assert (d, n) == (1, 1)
    assert type(d) is int
    d, n = False.as_integer_ratio()
    assert (d, n) == (0, 1)
    assert type(d) is int

    class X(int): pass
    a = X(5)
    n, d = a.as_integer_ratio()
    assert n == 5 and d == 1
    assert type(n) is int


def test_int_constructor_calls_index():
    class A:
        def __index__(self):
            return 25
    assert int(A()) == 25
    reallybig = 1 << 1000
    class A:
        def __index__(self):
            return reallybig
    assert int(A()) == reallybig

    class A:
        def __index__(self):
            return "abc"
    with pytest.raises(TypeError):
        int(A())

    class subint(int):
        pass
    class A:
        def __index__(self):
            return subint(12)
    x = int(A())
    assert x == 12
    assert type(x) is int


def test_bit_count():
    for x in (42, 2**100, 2**63, 2**63-1, 2**31-1, 2**31):
        assert x.bit_count() == bin(x).count("1")
        assert (-x).bit_count() == bin(x).count("1")
