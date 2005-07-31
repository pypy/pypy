import autopath
from pypy.lib._stablecompiler.transformer import decode_numeric_literal


def test_decode_numeric_literal():
    # decimal integer
    numeric_decode('0', 0)
    numeric_decode('1', 1)
    numeric_decode('9', 9)
    numeric_decode('10', 10)
    numeric_decode('2117', 2117)
    # octal integer
    numeric_decode('03', 3)
    numeric_decode('010', 8)
    numeric_decode('002117', 1103)
    # hexadecimal integer
    numeric_decode('0x0', 0)
    numeric_decode('0XE', 14)
    numeric_decode('0x002117', 8471)
    # decimal long
    numeric_decode('0l', 0L)
    numeric_decode('1L', 1L)
    numeric_decode('9l', 9L)
    numeric_decode('10L', 10L)
    numeric_decode('2117l', 2117L)
    # octal long
    numeric_decode('03L', 3L)
    numeric_decode('010l', 8L)
    numeric_decode('002117L', 1103L)
    # hexadecimal long
    numeric_decode('0x0l', 0L)
    numeric_decode('0XEL', 14L)
    numeric_decode('0x002117l', 8471L)
    # automatic long results for ints that are too large
    numeric_decode('99999999999999999999999999999999999999999999999999999',
                    99999999999999999999999999999999999999999999999999999)
    numeric_decode('0xdeadbeef', int('deadbeef', 16))
    numeric_decode('01236417564174623643237641763',
                    01236417564174623643237641763)
    # floating point
    numeric_decode('3.25', 3.25)
    numeric_decode('10.', 10.0)
    numeric_decode('.015625', 0.015625)
    numeric_decode('0.015625', 0.015625)
    numeric_decode('00.015625', 0.015625)
    numeric_decode('1e100', 1e100)
    numeric_decode('1.5625E-2', 0.015625)
    numeric_decode('1.5625e-000000000002', 0.015625)
    numeric_decode('0e0', 0.0)
    # imaginary number
    numeric_decode('0j', 0.0j)
    numeric_decode('1J', 1.0j)
    numeric_decode('9j', 9.0j)
    numeric_decode('10J', 10.0j)
    numeric_decode('2117j', 2117.0j)
    numeric_decode('03J', 3.0j)
    numeric_decode('010j', 10.0j)
    numeric_decode('002117J', 2117.0j)
    numeric_decode('3.25j', 3.25j)
    numeric_decode('10.J', 10.0j)
    numeric_decode('.015625j', 0.015625j)
    numeric_decode('0.015625J', 0.015625j)
    numeric_decode('00.015625j', 0.015625j)
    numeric_decode('1e100J', 1e100j)
    numeric_decode('1.5625E-2j', 0.015625j)
    numeric_decode('1.5625e-000000000002J', 0.015625j)
    numeric_decode('0e0j', 0.0j)


def numeric_decode(string, expected):
    result = decode_numeric_literal(string)
    assert result == expected
    assert type(result) == type(expected)
