import pytest

from pypy.interpreter.location import (encode_positions,
    decode_positions, _offset2lineno, linetable2lnotab)

def check_positions(positions, firstlineno=1, expected=None):
    if expected is None:
        expected = positions
    res = decode_positions(
        encode_positions(positions, firstlineno),
        firstlineno
    )
    assert res == expected

def test_encode_positions():
    # valid
    positions = [(1, 1, 1, 5), (1, 1, 5, 10), (2, 2, 5, 10)]
    check_positions(positions)
    check_positions(positions, 0)

def test_encode_positions_invalid():
    #                          everything invalid
    positions = [(1, 1, 1, 5), (-1, -1, -1, -1), (2, 2, 5, 10)]
    check_positions(positions)
    check_positions(positions, 0)

def test_encode_positions_invalid_but_lineno_is_fine():
    #                          just lineno valid
    positions = [(1, 1, 1, 5), (1, -1, -1, -1), (2, 2, 5, 10)]
    check_positions(positions)
    check_positions(positions, 0)

def test_out_of_range_positions():
    positions = [
        (5, 1000, 1, 1), # too large end_lineno - lineno
        (6, 1, 300, 400), # col_offset too big
        (6, 1, 0, 300), # end_col_offset too big
        (7, 1, 3, 2), # end_lineno smaller than lineno
    ]
    check_positions(positions, expected=[(5, -1, -1, -1), (6, -1, -1, -1), (6, -1, -1, -1), (7, -1, -1, -1)])


def test_offset2lineno():
    positions = [(lineno, lineno, 1, 1) for lineno in [1, 1, 5, 3, 23, 1999]]
    table = encode_positions(positions, 1)
    for stopat in range(len(positions)):
        assert _offset2lineno(table, 1, stopat) == positions[stopat][0]


def lnotab_offset2lineno(tab, line, stopat):
    addr = 0
    for i in range(0, len(tab), 2):
        addr = addr + ord(tab[i])
        if addr > stopat:
            break
        line_offset = ord(tab[i+1])
        if line_offset > 0x80:
            line_offset -= 0x100
        line = line + line_offset
    return line

def test_linetable2lnotab():
    positions = [(lineno, lineno, 1, 1) for lineno in [1, 1, 1, 3, 3, 2, 2, 17]]
    table = encode_positions(positions, 1)
    lnotab = linetable2lnotab(table, 1)
    # check that the bdeltas are even
    for bdelta in lnotab[::2]:
        assert ord(bdelta) & 1 == 0
    for stopat in range(len(positions)):
        assert lnotab_offset2lineno(lnotab, 1, stopat * 2) == positions[stopat][0]
