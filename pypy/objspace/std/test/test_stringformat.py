import autopath
from pypy.tool import testit


class TestStringObjectWithDict(testit.AppTestCase):

    def setUp(self):
        # force testing to use standard objspace
        self.space = testit.objspace('std')

    def test_format_item(self):
        d = {'i': 23}
        self.assertEquals('a23b', 'a%(i)sb' % d)
        self.assertEquals('23b', '%(i)sb' % d)
        self.assertEquals('a23', 'a%(i)s' % d)
        self.assertEquals('23', '%(i)s' % d)

    def test_format_two_items(self):
        d = {'i': 23, 'j': 42}
        self.assertEquals('a23b42c', 'a%(i)sb%(j)sc' % d)
        self.assertEquals('a23b23c', 'a%(i)sb%(i)sc' % d)

    def test_format_percent(self):
        self.assertEquals('a%b', 'a%%b' % {}) 

    def test_format_empty_key(self):
        d = {'':42}
        self.assertEquals('42', '%()s' % d)

    def test_format_wrong_char(self):
        d = {'i': 23}
        self.assertRaises(ValueError, 'a%(i)Zb'.__mod__, d) 

    def test_format_missing(self):
        d = {'i': 23}
        self.assertRaises(KeyError, 'a%(x)sb'.__mod__, d) 

class TestStringObject(testit.AppTestCase):

    def setUp(self):
        # force testing to use standard objspace
        self.space = testit.objspace('std')

    def test_format_item(self):
        self.assertEquals('a23b', 'a%sb' % 23)
        self.assertEquals('23b', '%sb' % 23)
        self.assertEquals('a23', 'a%s' % 23)
        self.assertEquals('23', '%s' % 23)

    def test_format_percent(self):
        self.assertEquals('a%b', 'a%%b' % ())
        self.assertEquals('%b', '%%b' % ())
        self.assertEquals('a%', 'a%%' % ())
        self.assertEquals('%', '%%' % ())

    def test_format_too_much(self):
        self.assertRaises(TypeError, '%s%s'.__mod__, ())
        self.assertRaises(TypeError, '%s%s'.__mod__, (23,))

    def test_format_not_enough(self):
        self.assertRaises(TypeError, '%s%s'.__mod__, (23,)*3)
        self.assertRaises(TypeError, '%s%s'.__mod__, (23,)*4)

    def test_format_string(self):
        self.assertEquals('23', '%s' % '23')
        self.assertEquals("'23'", '%r' % '23')
        self.assertRaises(TypeError, '%d'.__mod__, "23")

    def test_format_float(self):
        self.assertEquals('23', '%d' % 23.456)
        self.assertEquals('0x17', '%x' % 23.456)
        self.assertEquals('23.456', '%s' % 23.456)
        # accept either exact or filled-with-9's for %r
        r = '%r' % 23.45
        if len(r)==5:
            self.assertEquals('23.45', r)
        else:
            r9 = '23.44' + '9'*(len(r)-5)
            self.assertEquals(r9, r)

    def test_format_int(self):
        self.assertEquals('23', '%d' % 23)
        self.assertEquals('0x17', '%x' % 23)
        self.assertEquals('23', '%s' % 23)
        self.assertEquals('23', '%r' % 23)

    def test_format_wrong_char(self):
        self.assertRaises(ValueError, 'a%Zb'.__mod__, ((23,),))

class TestWidthPrec(testit.AppTestCase):
    def setUp(self):
        self.space = testit.objspace()

    def test_width(self):
        self.assertEquals("%3s"%'a', '  a')
        self.assertEquals("%-3s"%'a', 'a  ')

    def test_prec_string(self):
        self.assertEquals("%.3s"%'a', 'a')
        self.assertEquals("%.3s"%'abcde', 'abc')

    def test_prec_width_string(self):
        self.assertEquals("%5.3s"%'a',      '    a')
        self.assertEquals("%5.3s"%'abcde',  '  abc')
        self.assertEquals("%-5.3s"%'a',     'a    ')
        self.assertEquals("%-5.3s"%'abcde', 'abc  ')
        

if __name__ == '__main__':
    testit.main()
