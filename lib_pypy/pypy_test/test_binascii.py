from __future__ import absolute_import
import py
from lib_pypy import binascii

# Create binary test data
data = "The quick brown fox jumps over the lazy dog.\r\n"
# Be slow so we don't depend on other modules
data += "".join(map(chr, xrange(256)))
data += "\r\nHello world.\n"

def test_exceptions():
    # Check module exceptions
    assert issubclass(binascii.Error, Exception)
    assert issubclass(binascii.Incomplete, Exception)

def test_functions():
    # Check presence of all functions
    funcs = []
    for suffix in "base64", "hqx", "uu", "hex":
        prefixes = ["a2b_", "b2a_"]
        if suffix == "hqx":
            prefixes.extend(["crc_", "rlecode_", "rledecode_"])
        for prefix in prefixes:
            name = prefix + suffix
            assert callable(getattr(binascii, name))
            py.test.raises(TypeError, getattr(binascii, name))
    for name in ("hexlify", "unhexlify"):
        assert callable(getattr(binascii, name))
        py.test.raises(TypeError, getattr(binascii, name))

def test_base64valid():
    # Test base64 with valid data
    MAX_BASE64 = 57
    lines = []
    for i in range(0, len(data), MAX_BASE64):
        b = data[i:i+MAX_BASE64]
        a = binascii.b2a_base64(b)
        lines.append(a)
    res = ""
    for line in lines:
        b = binascii.a2b_base64(line)
        res = res + b
    assert res == data

def test_base64invalid():
    # Test base64 with random invalid characters sprinkled throughout
    # (This requires a new version of binascii.)
    MAX_BASE64 = 57
    lines = []
    for i in range(0, len(data), MAX_BASE64):
        b = data[i:i+MAX_BASE64]
        a = binascii.b2a_base64(b)
        lines.append(a)

    fillers = ""
    valid = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/"
    for i in xrange(256):
        c = chr(i)
        if c not in valid:
            fillers += c
    def addnoise(line):
        noise = fillers
        ratio = len(line) // len(noise)
        res = ""
        while line and noise:
            if len(line) // len(noise) > ratio:
                c, line = line[0], line[1:]
            else:
                c, noise = noise[0], noise[1:]
            res += c
        return res + noise + line
    res = ""
    for line in map(addnoise, lines):
        b = binascii.a2b_base64(line)
        res += b
    assert res == data

    # Test base64 with just invalid characters, which should return
    # empty strings. TBD: shouldn't it raise an exception instead ?
    assert binascii.a2b_base64(fillers) == ''

def test_uu():
    MAX_UU = 45
    lines = []
    for i in range(0, len(data), MAX_UU):
        b = data[i:i+MAX_UU]
        a = binascii.b2a_uu(b)
        lines.append(a)
    res = ""
    for line in lines:
        b = binascii.a2b_uu(line)
        res += b
    assert res == data

    assert binascii.a2b_uu("\x7f") == "\x00"*31
    assert binascii.a2b_uu("\x80") == "\x00"*32
    assert binascii.a2b_uu("\xff") == "\x00"*31
    py.test.raises(binascii.Error, binascii.a2b_uu, "\xff\x00")
    py.test.raises(binascii.Error, binascii.a2b_uu, "!!!!")

    py.test.raises(binascii.Error, binascii.b2a_uu, 46*"!")

def test_crc32():
    crc = binascii.crc32("Test the CRC-32 of")
    crc = binascii.crc32(" this string.", crc)
    assert crc == 1571220330
    
    crc = binascii.crc32('frotz\n', 0)
    assert crc == -372923920

    py.test.raises(TypeError, binascii.crc32)

def test_hex():
    # test hexlification
    s = '{s\005\000\000\000worldi\002\000\000\000s\005\000\000\000helloi\001\000\000\0000'
    t = binascii.b2a_hex(s)
    u = binascii.a2b_hex(t)
    assert s == u
    py.test.raises(TypeError, binascii.a2b_hex, t[:-1])
    py.test.raises(TypeError, binascii.a2b_hex, t[:-1] + 'q')

    # Verify the treatment of Unicode strings
    assert binascii.hexlify(unicode('a', 'ascii')) == '61'

def test_qp():
    # A test for SF bug 534347 (segfaults without the proper fix)
    try:
        binascii.a2b_qp("", **{1:1})
    except TypeError:
        pass
    else:
        fail("binascii.a2b_qp(**{1:1}) didn't raise TypeError")
    assert binascii.a2b_qp("= ") == "= "
    assert binascii.a2b_qp("==") == "="
    assert binascii.a2b_qp("=AX") == "=AX"
    py.test.raises(TypeError, binascii.b2a_qp, foo="bar")
    assert binascii.a2b_qp("=00\r\n=00") == "\x00\r\n\x00"
    assert binascii.b2a_qp("\xff\r\n\xff\n\xff") == "=FF\r\n=FF\r\n=FF"
    target = "0"*75+"=\r\n=FF\r\n=FF\r\n=FF"
    assert binascii.b2a_qp("0"*75+"\xff\r\n\xff\r\n\xff") == target

def test_empty_string():
    # A test for SF bug #1022953.  Make sure SystemError is not raised.
    for n in ['b2a_qp', 'a2b_hex', 'b2a_base64', 'a2b_uu', 'a2b_qp',
              'b2a_hex', 'unhexlify', 'hexlify', 'crc32', 'b2a_hqx',
              'a2b_hqx', 'a2b_base64', 'rlecode_hqx', 'b2a_uu',
              'rledecode_hqx']:
        f = getattr(binascii, n)
        f('')
    binascii.crc_hqx('', 0)

def test_qp_bug_case():
    assert binascii.b2a_qp('y'*77, False, False) == 'y'*75 + '=\nyy'
    assert binascii.b2a_qp(' '*77, False, False) == ' '*75 + '=\n =20'
    assert binascii.b2a_qp('y'*76, False, False) == 'y'*76
    assert binascii.b2a_qp(' '*76, False, False) == ' '*75 + '=\n=20'

def test_wrong_padding():
    s = 'CSixpLDtKSC/7Liuvsax4iC6uLmwMcijIKHaILzSwd/H0SC8+LCjwLsgv7W/+Mj3IQ'
    py.test.raises(binascii.Error, binascii.a2b_base64, s)

def test_crap_after_padding():
    s = 'xxx=axxxx'
    assert binascii.a2b_base64(s) == '\xc7\x1c'

def test_wrong_args():
    # this should grow as a way longer list
    py.test.raises(TypeError, binascii.a2b_base64, 42)
