
from pypy.module._rawffi.structure import size_alignment_pos
from pypy.module._rawffi.interp_rawffi import TYPEMAP, letter2tp

sizeof = lambda x : size_alignment_pos(x)[0]

def unpack(desc):
    return [('x', letter2tp('space', i)) for i in desc]

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
