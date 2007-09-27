from pypy.module.struct.ieee import pack_float, unpack_float


testcases = [
    (-0.025, 4, False, '\xcd\xcc\xcc\xbc'),
    (2.0 ** 100, 4, False, '\x00\x00\x80q'),
    (0.0, 4, True, '\x00\x00\x00\x00'),
    (-12345, 4, True, '\xc6@\xe4\x00'),
    (-0.025, 8, False, '\x9a\x99\x99\x99\x99\x99\x99\xbf'),
    (2.0 ** 100, 8, False, '\x00\x00\x00\x00\x00\x000F'),
    (0.0, 8, True, '\x00\x00\x00\x00\x00\x00\x00\x00'),
    (-123456789, 8, True, '\xc1\x9do4T\x00\x00\x00'),
    ]


def test_pack():
    for number, size, bigendian, expected in testcases:
        res = []
        pack_float(res, number, size, bigendian)
        assert res == list(expected)


def test_unpack():
    for expected, size, bigendian, input in testcases:
        assert len(input) == size
        res = unpack_float(input, bigendian)
        if size == 8:
            assert res == expected    # exact result expected
        else:
            assert abs(res - expected) < 1E-6
