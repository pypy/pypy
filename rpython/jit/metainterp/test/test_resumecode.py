
from rpython.jit.metainterp.resumecode import NUMBERING, NULL_NUMBER
from rpython.jit.metainterp.resumecode import create_numbering,\
    unpack_numbering, copy_from_list_to_numb
from rpython.rtyper.lltypesystem import lltype

def test_pack_unpack():
    examples = [
        [1, 2, 3, 4, 257, 10000, 13, 15],
        [1, 2, 3, 4],
        range(1, 10, 2),
        [13000, 12000, 10000, 256, 255, 254, 257, -3, -1000]
    ]
    for l in examples:
        n = create_numbering(l, NULL_NUMBER, 0)
        assert unpack_numbering(n) == l
