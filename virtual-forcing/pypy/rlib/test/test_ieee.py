import sys
from pypy.rlib.rstruct.ieee import pack_float, unpack_float
from pypy.rlib.rarithmetic import isinf, isnan

testcases = [
    (-0.025, 4, False, '\xcd\xcc\xcc\xbc'),
    (2.0 ** 100, 4, False, '\x00\x00\x80q'),
    (0.0, 4, True, '\x00\x00\x00\x00'),
    (-12345, 4, True, '\xc6@\xe4\x00'),
    (-0.025, 8, False, '\x9a\x99\x99\x99\x99\x99\x99\xbf'),
    (2.0 ** 100, 8, False, '\x00\x00\x00\x00\x00\x000F'),
    (0.0, 8, True, '\x00\x00\x00\x00\x00\x00\x00\x00'),
    (-123456789, 8, True, '\xc1\x9do4T\x00\x00\x00'),
    (1e200*1e200, 4, False, '\x00\x00\x80\x7f'),
    (-1e200*1e200, 4, False, '\x00\x00\x80\xff'),
    ((1e200*1e200)/(1e200*1e200), 4, False, '\x00\x00\xc0\xff'),
    (1e200*1e200, 8, False, '\x00\x00\x00\x00\x00\x00\xf0\x7f'),
    (-1e200*1e200, 8, False, '\x00\x00\x00\x00\x00\x00\xf0\xff'),
    ((1e200*1e200)/(1e200*1e200), 8, False, '\x00\x00\x00\x00\x00\x00\xf8\xff')
    ]


def test_correct_tests():
    import struct
    for number, size, bigendian, expected in testcases:
        if sys.version < (2, 5) and (isinf(number) or isnan(number)):
            continue    # 'inf' and 'nan' unsupported in CPython 2.4's struct
        if bigendian:
            fmt = '>'
        else:
            fmt = '<'
        if size == 4:
            fmt += 'f'
        else:
            fmt += 'd'
        assert struct.pack(fmt, number) == expected
        res, = struct.unpack(fmt, expected)
        assert (isnan(res) and isnan(number)) or \
                res == number or abs(res - number) < 1E-6

def test_pack():
    for number, size, bigendian, expected in testcases:
        print 'test_pack:', number, size, bigendian
        res = []
        pack_float(res, number, size, bigendian)
        assert ''.join(res) == expected


def test_unpack():
    for expected, size, bigendian, input in testcases:
        print 'test_unpack:', expected, size, bigendian
        assert len(input) == size
        res = unpack_float(input, bigendian)
        if isnan(res) and isnan(expected):
            pass
        else:
            if size == 8:
                assert res == expected    # exact result expected
            else:
                assert res == expected or abs(res - expected) < 1E-6


def test_llinterpreted():
    from pypy.rpython.test.test_llinterp import interpret
    def f():
        test_pack()
        test_unpack()
    interpret(f, [])
