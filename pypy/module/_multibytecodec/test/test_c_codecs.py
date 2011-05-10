from pypy.module._multibytecodec.c_codecs import getcodec, codecs


def test_codecs_existence():
    for name in codecs:
        c = getcodec(name)
        assert c
    c = getcodec("foobar")
    assert not c
