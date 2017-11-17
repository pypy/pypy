from pypy.interpreter.unicodehelper import str_decode_utf8
from pypy.interpreter.unicodehelper import utf8_encode_ascii, str_decode_ascii

def decode_utf8(u):
    return str_decode_utf8(u, True, "strict", None)

def test_decode_utf8():
    assert decode_utf8("abc") == ("abc", 3)
    assert decode_utf8("\xe1\x88\xb4") == ("\xe1\x88\xb4", 1)
    assert decode_utf8("\xed\xa0\x80") == ("\xed\xa0\x80", 1)
    assert decode_utf8("\xed\xb0\x80") == ("\xed\xb0\x80", 1)
    assert decode_utf8("\xed\xa0\x80\xed\xb0\x80") == (
        "\xed\xa0\x80\xed\xb0\x80", 2)
    assert decode_utf8("\xf0\x90\x80\x80") == ("\xf0\x90\x80\x80", 1)

def test_utf8_encode_ascii():
    assert utf8_encode_ascii("abc", 3, "??", "??") == "abc"
    def eh(errors, encoding, reason, p, start, end):
        lst.append((errors, encoding, p, start, end))
        return "<FOO>", end
    lst = []
    input = u"\u1234".encode("utf8")
    assert utf8_encode_ascii(input, 1, "??", eh) == "<FOO>"
    assert lst == [("??", "ascii", input, 0, 1)]
    lst = []
    input = u"\u1234\u5678abc\u8765\u4321".encode("utf8")
    assert utf8_encode_ascii(input, 7, "??", eh) == "<FOO>abc<FOO>"
    assert lst == [("??", "ascii", input, 0, 2),
                   ("??", "ascii", input, 5, 7)]

def test_str_decode_ascii():
    assert str_decode_ascii("abc", 3, "??", True, "??") == ("abc", 3, 3)
    def eh(errors, encoding, reason, p, start, end):
        lst.append((errors, encoding, p, start, end))
        return u"\u1234\u5678", end
    lst = []
    input = "\xe8"
    exp = u"\u1234\u5678".encode("utf8")
    assert str_decode_ascii(input, 1, "??", True, eh) == (exp, 1, 2)
    assert lst == [("??", "ascii", input, 0, 1)]
    lst = []
    input = "\xe8\xe9abc\xea\xeb"
    assert str_decode_ascii(input, 7, "??", True, eh) == (
        exp + exp + "abc" + exp + exp, 7, 11)
    assert lst == [("??", "ascii", input, 0, 1),
                   ("??", "ascii", input, 1, 2),
                   ("??", "ascii", input, 5, 6),
                   ("??", "ascii", input, 6, 7)]
