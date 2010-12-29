
from pypy.module._rawffi.structure import size_alignment_pos
from pypy.module._rawffi.interp_rawffi import TYPEMAP, letter2tp

sizeof = lambda x : size_alignment_pos(x)[0]

def unpack(desc):
    return [('x', letter2tp('space', i), 0) for i in desc]

def test_sizeof():
    s_c = sizeof(unpack('c'))
    s_l = sizeof(unpack('l'))
    s_q = sizeof(unpack('q'))
    alignment_of_q = TYPEMAP['q'].c_alignment
    assert alignment_of_q >= 4
    assert sizeof(unpack('cl')) == 2*s_l
    assert sizeof(unpack('cq')) == alignment_of_q + s_q
    assert sizeof(unpack('ccq')) == alignment_of_q + s_q
    assert sizeof(unpack('cccq')) == alignment_of_q + s_q
    assert sizeof(unpack('ccccq')) == alignment_of_q + s_q
    assert sizeof(unpack('qc')) == s_q + alignment_of_q
    assert sizeof(unpack('qcc')) == s_q + alignment_of_q
    assert sizeof(unpack('qccc')) == s_q + alignment_of_q
    assert sizeof(unpack('qcccc')) == s_q + alignment_of_q

def test_bitsizes():
    c_int = letter2tp('space', 'i')
    c_short = letter2tp('space', 'h')
    fields = [("A", c_int, 1),
              ("B", c_int, 2),
              ("C", c_int, 3),
              ("D", c_int, 4),
              ("E", c_int, 5),
              ("F", c_int, 6),
              ("G", c_int, 7),
              ("H", c_int, 8),
              ("I", c_int, 9),

              ("M", c_short, 1),
              ("N", c_short, 2),
              ("O", c_short, 3),
              ("P", c_short, 4),
              ("Q", c_short, 5),
              ("R", c_short, 6),
              ("S", c_short, 7)]
    size, alignment, pos, bitsizes = size_alignment_pos(fields)
    assert size == 12
    assert pos == [0, 0, 0, 0, 0, 0, 0, 4, 4, 8, 8, 8, 8, 8, 10, 10]
    assert bitsizes == [
        0x10000, 0x20001, 0x30003, 0x40006, 0x5000a, 0x6000f, 0x70015, 0x80000, 0x90008,
        0x10000, 0x20001, 0x30003, 0x40006, 0x5000a, 0x60000, 0x70006]

    # TODO: test a normal struct containing a big array > 0x10000.
    # Make sure we don't take this for a bitsize...
