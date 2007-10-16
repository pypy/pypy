
from pypy.module._ffi.structure import size_and_pos

sizeof = lambda x : size_and_pos(x)[0]

def unpack(desc):
    return [('x', i) for i in desc]

def test_sizeof():
    s_c = sizeof(unpack('c'))
    s_l = sizeof(unpack('l'))
    s_q = sizeof(unpack('q'))
    assert sizeof(unpack('cl')) == 2*s_l
    assert sizeof(unpack('cq')) == s_q + s_l
    assert sizeof(unpack('ccq')) == s_q + s_l
    assert sizeof(unpack('ccccq')) == 4 * s_c + s_q

