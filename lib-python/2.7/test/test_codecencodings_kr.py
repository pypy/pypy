#
# test_codecencodings_kr.py
#   Codec encoding tests for ROK encodings.
#

from test import test_support
from test import multibytecodec_support
import unittest

class Test_CP949(multibytecodec_support.TestBase, unittest.TestCase):
    encoding = 'cp949'
    tstring = multibytecodec_support.load_teststring('cp949')
    codectests = (
        # invalid bytes
        (b"abc\x80\x80\xc1\xc4", "strict",  None),
        (b"abc\xc8", "strict",  None),
        (b"abc\x80\x80\xc1\xc4", "replace", u"abc\ufffd\ufffd\uc894"),
        (b"abc\x80\x80\xc1\xc4\xc8", "replace", u"abc\ufffd\ufffd\uc894\ufffd"),
        (b"abc\x80\x80\xc1\xc4", "ignore",  u"abc\uc894"),
    )

class Test_EUCKR(multibytecodec_support.TestBase, unittest.TestCase):
    encoding = 'euc_kr'
    tstring = multibytecodec_support.load_teststring('euc_kr')
    codectests = (
        # invalid bytes
        (b"abc\x80\x80\xc1\xc4", "strict",  None),
        (b"abc\xc8", "strict",  None),
        (b"abc\x80\x80\xc1\xc4", "replace", u'abc\ufffd\ufffd\uc894'),
        (b"abc\x80\x80\xc1\xc4\xc8", "replace", u"abc\ufffd\ufffd\uc894\ufffd"),
        (b"abc\x80\x80\xc1\xc4", "ignore",  u"abc\uc894"),

        # composed make-up sequence errors
        (b"\xa4\xd4", "strict", None),
        (b"\xa4\xd4\xa4", "strict", None),
        (b"\xa4\xd4\xa4\xb6", "strict", None),
        (b"\xa4\xd4\xa4\xb6\xa4", "strict", None),
        (b"\xa4\xd4\xa4\xb6\xa4\xd0", "strict", None),
        (b"\xa4\xd4\xa4\xb6\xa4\xd0\xa4", "strict", None),
        (b"\xa4\xd4\xa4\xb6\xa4\xd0\xa4\xd4", "strict", u"\uc4d4"),
        (b"\xa4\xd4\xa4\xb6\xa4\xd0\xa4\xd4x", "strict", u"\uc4d4x"),
        (b"a\xa4\xd4\xa4\xb6\xa4", "replace", u'a\ufffd'),
        (b"\xa4\xd4\xa3\xb6\xa4\xd0\xa4\xd4", "strict", None),
        (b"\xa4\xd4\xa4\xb6\xa3\xd0\xa4\xd4", "strict", None),
        (b"\xa4\xd4\xa4\xb6\xa4\xd0\xa3\xd4", "strict", None),
        (b"\xa4\xd4\xa4\xff\xa4\xd0\xa4\xd4", "replace", u'\ufffd\u6e21\ufffd\u3160\ufffd'),
        (b"\xa4\xd4\xa4\xb6\xa4\xff\xa4\xd4", "replace", u'\ufffd\u6e21\ub544\ufffd\ufffd'),
        (b"\xa4\xd4\xa4\xb6\xa4\xd0\xa4\xff", "replace", u'\ufffd\u6e21\ub544\u572d\ufffd'),
        (b"\xa4\xd4\xff\xa4\xd4\xa4\xb6\xa4\xd0\xa4\xd4", "replace", u'\ufffd\ufffd\ufffd\uc4d4'),
        (b"\xc1\xc4", "strict", u"\uc894"),
    )

class Test_JOHAB(multibytecodec_support.TestBase, unittest.TestCase):
    encoding = 'johab'
    tstring = multibytecodec_support.load_teststring('johab')
    codectests = (
        # invalid bytes
        (b"abc\x80\x80\xc1\xc4", "strict",  None),
        (b"abc\xc8", "strict",  None),
        (b"abc\x80\x80\xc1\xc4", "replace", u"abc\ufffd\ufffd\ucd27"),
        (b"abc\x80\x80\xc1\xc4\xc8", "replace", u"abc\ufffd\ufffd\ucd27\ufffd"),
        (b"abc\x80\x80\xc1\xc4", "ignore",  u"abc\ucd27"),
        (b"\xD8abc", "replace",  u"\ufffdabc"),
        (b"\xD8\xFFabc", "replace",  u"\ufffd\ufffdabc"),
        (b"\x84bxy", "replace",  u"\ufffdbxy"),
        (b"\x8CBxy", "replace",  u"\ufffdBxy"),
    )

def test_main():
    test_support.run_unittest(__name__)

if __name__ == "__main__":
    test_main()
