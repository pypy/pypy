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
