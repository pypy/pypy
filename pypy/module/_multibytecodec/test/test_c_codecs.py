from pypy.module._multibytecodec.c_codecs import getcodec, codecs
from pypy.module._multibytecodec.c_codecs import decode


def test_codecs_existence():
    for name in codecs:
        c = getcodec(name)
        assert c
    c = getcodec("foobar")
    assert not c

def test_gbk_simple():
    c = getcodec("gbk")
    u = decode(c, "\xA1\xAA")
    assert u == unichr(0x2014)
