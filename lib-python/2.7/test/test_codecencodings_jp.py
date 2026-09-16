#
# test_codecencodings_jp.py
#   Codec encoding tests for Japanese encodings.
#

from test import test_support
from test import multibytecodec_support
import unittest

class Test_CP932(multibytecodec_support.TestBase, unittest.TestCase):
    encoding = 'cp932'
    tstring = multibytecodec_support.load_teststring('shift_jis')
    codectests = (
        # invalid bytes
        (b"abc\x81\x00\x81\x00\x82\x84", "strict",  None),
        (b"abc\xf8", "strict",  None),
        (b"abc\x81\x00\x82\x84", "replace", u"abc\ufffd\x00\uff44"),
        (b"abc\x81\x00\x82\x84\x88", "replace", u"abc\ufffd\x00\uff44\ufffd"),
        (b"abc\x81\x00\x82\x84", "ignore",  u"abc\x00\uff44"),
        (b"ab\xEBxy", "replace", u"ab\ufffdxy"),
        (b"ab\xF0\x39xy", "replace", u"ab\ufffd9xy"),
        (b"ab\xEA\xF0xy", "replace", u'ab\ufffd\ue038y'),
        # sjis vs cp932
        (b"\\\x7e", "replace", u"\\\x7e"),
        (b"\x81\x5f\x81\x61\x81\x7c", "replace", u"\uff3c\u2225\uff0d"),
    )

euc_commontests = (
    # invalid bytes
    (b"abc\x80\x80\xc1\xc4", "strict",  None),
    (b"abc\x80\x80\xc1\xc4", "replace", u"abc\ufffd\ufffd\u7956"),
    (b"abc\x80\x80\xc1\xc4\xc8", "replace", u"abc\ufffd\ufffd\u7956\ufffd"),
    (b"abc\x80\x80\xc1\xc4", "ignore",  u"abc\u7956"),
    (b"abc\xc8", "strict",  None),
    (b"abc\x8f\x83\x83", "replace", u"abc\ufffd\ufffd\ufffd"),
    (b"\x82\xFCxy", "replace", u"\ufffd\ufffdxy"),
    (b"\xc1\x64", "strict", None),
    (b"\xa1\xc0", "strict", u"\uff3c"),
    (b"\xa1\xc0\\", "strict", u"\uff3c\\"),
    (b"\x8eXY", "replace", u"\ufffdXY"),
)

class Test_EUC_JIS_2004(multibytecodec_support.TestBase,
                        unittest.TestCase):
    encoding = 'euc_jis_2004'
    tstring = multibytecodec_support.load_teststring('euc_jisx0213')
    codectests = euc_commontests
    xmlcharnametest = (
        u"\xab\u211c\xbb = \u2329\u1234\u232a",
        b"\xa9\xa8&real;\xa9\xb2 = &lang;&#4660;&rang;"
    )

class Test_EUC_JISX0213(multibytecodec_support.TestBase,
                        unittest.TestCase):
    encoding = 'euc_jisx0213'
    tstring = multibytecodec_support.load_teststring('euc_jisx0213')
    codectests = euc_commontests
    xmlcharnametest = (
        u"\xab\u211c\xbb = \u2329\u1234\u232a",
        b"\xa9\xa8&real;\xa9\xb2 = &lang;&#4660;&rang;"
    )

class Test_EUC_JP_COMPAT(multibytecodec_support.TestBase,
                         unittest.TestCase):
    encoding = 'euc_jp'
    tstring = multibytecodec_support.load_teststring('euc_jp')
    codectests = euc_commontests + (
        (u"\xa5", "strict", b"\x5c"),
        (u"\u203e", "strict", b"\x7e"),
    )

shiftjis_commonenctests = (
    (b"abc\x80\x80\x82\x84", "strict",  None),
    (b"abc\xf8", "strict",  None),
    (b"abc\x80\x80\x82\x84def", "ignore",  u"abc\uff44def"),
)

class Test_SJIS_COMPAT(multibytecodec_support.TestBase, unittest.TestCase):
    encoding = 'shift_jis'
    tstring = multibytecodec_support.load_teststring('shift_jis')
    codectests = shiftjis_commonenctests + (
        (b"abc\x80\x80\x82\x84", "replace", u"abc\ufffd\ufffd\uff44"),
        (b"abc\x80\x80\x82\x84\x88", "replace", u"abc\ufffd\ufffd\uff44\ufffd"),

        (b"\\\x7e", "strict", u"\\\x7e"),
        (b"\x81\x5f\x81\x61\x81\x7c", "strict", u"\uff3c\u2016\u2212"),
        (b"abc\x81\x39", "replace",  u"abc\ufffd9"),
        (b"abc\xEA\xFC", "replace",  u"abc\ufffd\ufffd"),
        (b"abc\xFF\x58", "replace",  u"abc\ufffdX"),
    )

class Test_SJIS_2004(multibytecodec_support.TestBase, unittest.TestCase):
    encoding = 'shift_jis_2004'
    tstring = multibytecodec_support.load_teststring('shift_jis')
    codectests = shiftjis_commonenctests + (
        (b"\\\x7e", "strict", u"\xa5\u203e"),
        (b"\x81\x5f\x81\x61\x81\x7c", "strict", u"\\\u2016\u2212"),
        (b"abc\xEA\xFC", "strict",  u"abc\u64bf"),
        (b"\x81\x39xy", "replace",  u"\ufffd9xy"),
        (b"\xFF\x58xy", "replace",  u"\ufffdXxy"),
        (b"\x80\x80\x82\x84xy", "replace", u"\ufffd\ufffd\uff44xy"),
        (b"\x80\x80\x82\x84\x88xy", "replace", u"\ufffd\ufffd\uff44\u5864y"),
        (b"\xFC\xFBxy", "replace", u'\ufffd\u95b4y'),
    )
    xmlcharnametest = (
        u"\xab\u211c\xbb = \u2329\u1234\u232a",
        b"\x85G&real;\x85Q = &lang;&#4660;&rang;"
    )

class Test_SJISX0213(multibytecodec_support.TestBase, unittest.TestCase):
    encoding = 'shift_jisx0213'
    tstring = multibytecodec_support.load_teststring('shift_jisx0213')
    codectests = shiftjis_commonenctests + (
        (b"abc\x80\x80\x82\x84", "replace", u"abc\ufffd\ufffd\uff44"),
        (b"abc\x80\x80\x82\x84\x88", "replace", u"abc\ufffd\ufffd\uff44\ufffd"),

        # sjis vs cp932
        (b"\\\x7e", "replace", u"\xa5\u203e"),
        (b"\x81\x5f\x81\x61\x81\x7c", "replace", u"\x5c\u2016\u2212"),
    )
    xmlcharnametest = (
        u"\xab\u211c\xbb = \u2329\u1234\u232a",
        b"\x85G&real;\x85Q = &lang;&#4660;&rang;"
    )

def test_main():
    test_support.run_unittest(__name__)

if __name__ == "__main__":
    test_main()
