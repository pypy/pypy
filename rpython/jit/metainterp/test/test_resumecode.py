
from rpython.jit.metainterp.resumecode import NUMBERING, NULL_NUMBER
from rpython.jit.metainterp.resumecode import create_numbering,\
    unpack_numbering
from rpython.rtyper.lltypesystem import lltype

from hypothesis import strategies, given


def test_pack_unpack():
    examples = [
        [1, 2, 3, 4, 257, 10000, 13, 15],
        [1, 2, 3, 4],
        range(1, 10, 2),
        [13000, 12000, 10000, 256, 255, 254, 257, -3, -1000]
    ]
    for l in examples:
        n = create_numbering(l)
        assert unpack_numbering(n) == l

@given(strategies.lists(strategies.integers(-2**15, 2**15-1)))
def test_roundtrip(l):
    n = create_numbering(l)
    assert unpack_numbering(n) == l

@given(strategies.lists(strategies.integers(-2**15, 2**15-1)))
def test_compressing(l):
    n = create_numbering(l)
    assert len(n.code) <= len(l) * 3
