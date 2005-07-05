# test the integration of unicode and strings (even though we don't
# really implement unicode yet).

import autopath, sys


objspacename = 'std'

class AppTestUnicodeStringStdOnly:
    def test_compares(self):
        assert u'a' == 'a'
        assert 'a' == u'a'
        assert not u'a' == 'b' # xxx u'a' != 'b' fails
        assert not 'a'  == u'b'# xxx 'a' != u'b' fails

class AppTestUnicodeString:
    def test_addition(self):
        def check(a, b):
            assert a == b
            assert type(a) == type(b)
        check(u'a' + 'b', u'ab')
        check('a' + u'b', u'ab')

    def test_join(self):
        def check(a, b):
            assert a == b
            assert type(a) == type(b)
        check(', '.join([u'a']), u'a')
        check(', '.join(['a', u'b']), u'a, b')
        check(u', '.join(['a', 'b']), u'a, b')

    if sys.version_info >= (2,3):
        def test_contains_ex(self):
            assert u'' in 'abc'
            assert u'bc' in 'abc'
            assert 'bc' in 'abc'

    def test_contains(self):
        assert u'a' in 'abc'
        assert 'a' in u'abc'

    def test_splitlines(self):
        assert u''.splitlines() == []
        assert u''.splitlines(1) == []
        assert u'\n'.splitlines() == [u'']
        assert u'a'.splitlines() == [u'a']
        assert u'one\ntwo'.splitlines() == [u'one', u'two']
        assert u'\ntwo\nthree'.splitlines() == [u'', u'two', u'three']
        assert u'\n\n'.splitlines() == [u'', u'']
        assert u'a\nb\nc'.splitlines(1) == [u'a\n', u'b\n', u'c']
        assert u'\na\nb\n'.splitlines(1) == [u'\n', u'a\n', u'b\n']

    def test_zfill(self):
        assert u'123'.zfill(6) == u'000123'
        assert u'123'.zfill(2) == u'123'
        assert u'123'.zfill(6) == u'000123'
        assert u'+123'.zfill(2) == u'+123'
        assert u'+123'.zfill(4) == u'+123'
        assert u'+123'.zfill(6) == u'+00123'

    def test_split(self):
        assert u"".split() == []
        assert u" ".split() == []
        assert u"a".split() == [u'a']
        assert u"a".split(u"a", 1) == [u'', u'']
        assert u" ".split(u" ", 1) == [u'', u'']
        assert u"aa".split(u"a", 2) == [u'', u'', u'']
        assert u" a ".split() == [u'a']
        assert u"a b c".split() == [u'a',u'b',u'c']
        assert u'this is the split function'.split() == [u'this', u'is', u'the', u'split', u'function']
        assert u'a|b|c|d'.split(u'|') == [u'a', u'b', u'c', u'd']
        assert 'a|b|c|d'.split(u'|') == [u'a', u'b', u'c', u'd']
        assert u'a|b|c|d'.split('|') == [u'a', u'b', u'c', u'd']
        assert u'a|b|c|d'.split(u'|', 2) == [u'a', u'b', u'c|d']
        assert u'a b c d'.split(None, 1) == [u'a', u'b c d']
        assert u'a b c d'.split(None, 2) == [u'a', u'b', u'c d']
        assert u'a b c d'.split(None, 3) == [u'a', u'b', u'c', u'd']
        assert u'a b c d'.split(None, 4) == [u'a', u'b', u'c', u'd']
        assert u'a b c d'.split(None, 0) == [u'a b c d']
        assert u'a  b  c  d'.split(None, 2) == [u'a', u'b', u'c  d']
        assert u'a b c d '.split() == [u'a', u'b', u'c', u'd']
        assert u'a//b//c//d'.split(u'//') == [u'a', u'b', u'c', u'd']
        assert u'endcase test'.split(u'test') == [u'endcase ', u'']
        raises(ValueError, u'abc'.split, '')
        raises(ValueError, u'abc'.split, u'')
        raises(ValueError, 'abc'.split, u'')

    def test_rsplit(self):
        assert u"".rsplit() == []
        assert u" ".rsplit() == []
        assert u"a".rsplit() == [u'a']
        assert u"a".rsplit(u"a", 1) == [u'', u'']
        assert u" ".rsplit(u" ", 1) == [u'', u'']
        assert u"aa".rsplit(u"a", 2) == [u'', u'', u'']
        assert u" a ".rsplit() == [u'a']
        assert u"a b c".rsplit() == [u'a',u'b',u'c']
        assert u'this is the rsplit function'.rsplit() == [u'this', u'is', u'the', u'rsplit', u'function']
        assert u'a|b|c|d'.rsplit(u'|') == [u'a', u'b', u'c', u'd']
        assert u'a|b|c|d'.rsplit('|') == [u'a', u'b', u'c', u'd']
        assert 'a|b|c|d'.rsplit(u'|') == [u'a', u'b', u'c', u'd']
        assert u'a|b|c|d'.rsplit(u'|', 2) == [u'a|b', u'c', u'd']
        assert u'a b c d'.rsplit(None, 1) == [u'a b c', u'd']
        assert u'a b c d'.rsplit(None, 2) == [u'a b', u'c', u'd']
        assert u'a b c d'.rsplit(None, 3) == [u'a', u'b', u'c', u'd']
        assert u'a b c d'.rsplit(None, 4) == [u'a', u'b', u'c', u'd']
        assert u'a b c d'.rsplit(None, 0) == [u'a b c d']
        assert u'a  b  c  d'.rsplit(None, 2) == [u'a  b', u'c', u'd']
        assert u'a b c d '.rsplit() == [u'a', u'b', u'c', u'd']
        assert u'a//b//c//d'.rsplit(u'//') == [u'a', u'b', u'c', u'd']
        assert u'endcase test'.rsplit(u'test') == [u'endcase ', u'']
        raises(ValueError, u'abc'.rsplit, u'')
        raises(ValueError, u'abc'.rsplit, '')
        raises(ValueError, 'abc'.rsplit, u'')

    def test_center(self):
        s=u"a b"
        assert s.center(0) == u"a b"
        assert s.center(1) == u"a b"
        assert s.center(2) == u"a b"
        assert s.center(3) == u"a b"
        assert s.center(4) == u"a b "
        assert s.center(5) == u" a b "
        assert s.center(6) == u" a b  "
        assert s.center(7) == u"  a b  "
        assert s.center(8) == u"  a b   "
        assert s.center(9) == u"   a b   "
        assert u'abc'.center(10) == u'   abc    '
        assert u'abc'.center(6) == u' abc  '
        assert u'abc'.center(3) == u'abc'
        assert u'abc'.center(2) == u'abc'
        assert u'abc'.center(5, u'*') == u'*abc*'    # Python 2.4
        assert u'abc'.center(5, '*') == u'*abc*'     # Python 2.4
        raises(TypeError, u'abc'.center, 4, u'cba')

    def test_rjust(self):
        s = u"abc"
        assert s.rjust(2) == s
        assert s.rjust(3) == s
        assert s.rjust(4) == u" " + s
        assert s.rjust(5) == u"  " + s
        assert u'abc'.rjust(10) == u'       abc'
        assert u'abc'.rjust(6) == u'   abc'
        assert u'abc'.rjust(3) == u'abc'
        assert u'abc'.rjust(2) == u'abc'
        assert u'abc'.rjust(5, u'*') == u'**abc'    # Python 2.4
        assert u'abc'.rjust(5, '*') == u'**abc'     # Python 2.4
        raises(TypeError, u'abc'.rjust, 5, u'xx')

    def test_ljust(self):
        s = u"abc"
        assert s.ljust(2) == s
        assert s.ljust(3) == s
        assert s.ljust(4) == s + u" "
        assert s.ljust(5) == s + u"  "
        assert u'abc'.ljust(10) == u'abc       '
        assert u'abc'.ljust(6) == u'abc   '
        assert u'abc'.ljust(3) == u'abc'
        assert u'abc'.ljust(2) == u'abc'
        assert u'abc'.ljust(5, u'*') == u'abc**'    # Python 2.4
        assert u'abc'.ljust(5, '*') == u'abc**'     # Python 2.4
        raises(TypeError, u'abc'.ljust, 6, u'')

    def test_long_from_unicode(self):
        assert long(u'12345678901234567890') == 12345678901234567890
        assert int(u'12345678901234567890') == 12345678901234567890

    def test_int_from_unicode(self):
        assert int(u'12345') == 12345

    def test_float_from_unicode(self):
        assert float(u'123.456e89') == float('123.456e89')
