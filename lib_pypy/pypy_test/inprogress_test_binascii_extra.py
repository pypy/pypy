from __future__ import absolute_import
from lib_pypy import binascii

def test_uu():
    assert binascii.b2a_uu('1234567') == "',3(S-#4V-P  \n"
    assert binascii.b2a_uu('123456789012345678901234567890123456789012345') == 'M,3(S-#4V-S@Y,#$R,S0U-C<X.3 Q,C,T-38W.#DP,3(S-#4V-S@Y,#$R,S0U\n'
    try:
        assert binascii.b2a_uu('1234567890123456789012345678901234567890123456')
    except binascii.Error:
        pass
    else:
        assert False, "Expected binascii.Error on oversize input."
    assert binascii.b2a_uu('1234567') == "',3(S-#4V-P  \n"
    assert binascii.b2a_uu('123456789012345678901234567890123456789012345')  == 'M,3(S-#4V-S@Y,#$R,S0U-C<X.3 Q,C,T-38W.#DP,3(S-#4V-S@Y,#$R,S0U\n'


def test_base64():
    assert binascii.b2a_base64('xxxx') == 'eHh4eA==\n'

