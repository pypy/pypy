import autopath
from pypy.tool import testit


class TestStringObjectWithDict(testit.AppTestCase):

    def setUp(self):
        self.space = testit.objspace('std')

    def test_format_item(self):
        d = {'i': 23, '':42}
        self.assertEquals('a23b', 'a%(i)sb' % d)
        self.assertEquals('23b', '%(i)sb' % d)
        self.assertEquals('a23', 'a%(i)s' % d)
        self.assertEquals('23', '%(i)s' % d)
        self.assertEquals('a%b', 'a%%b' % d) 
        self.assertEquals('42', '%()s' % d)
        self.assertRaises(ValueError, 'a%()Zb'.__mod__, d) 

class TestStringObject(testit.AppTestCase):

    def setUp(self):
        self.space = testit.objspace('std')

    def test_format_item(self):
        self.assertEquals('a23b', 'a%sb' % 23)
        self.assertEquals('23b', '%sb' % 23)
        self.assertEquals('a23', 'a%s' % 23)
        self.assertEquals('23', '%s' % 23)
        self.assertEquals('a%b', 'a%%b' % ())
        self.assertEquals('%b', '%%b' % ())
        self.assertEquals('a%', 'a%%' % ())
        self.assertEquals('%', '%%' % ())

    def test_format_wronglength(self):
        self.assertRaises(TypeError, '%s%s'.__mod__, ())
        self.assertRaises(TypeError, '%s%s'.__mod__, (23,))
        self.assertRaises(TypeError, '%s%s'.__mod__, (23,)*3)
        self.assertRaises(TypeError, '%s%s'.__mod__, (23,)*4)

    def test_format_kinds(self):
        self.assertEquals('23', '%s' % '23')
        self.assertEquals("'23'", '%r' % '23')
        """ unclear behavior requirement, so commented for now...:
            self.assertEquals('23', '%d' % '23') ...or...:
            self.assertRaises(TypeError, '%d'.__mod__, ((23,),)) ...?
        """
        self.assertEquals('23', '%d' % 23.456)
        self.assertEquals('0x17', '%x' % 23.456)
        self.assertEquals('23.456', '%s' % 23.456)
        r = '%r' % 23.45
        if len(r)==5:
            self.assertEquals('23.45', r)
        else:
            r9 = '23.44' + '9'*(len(r)-5)
            self.assertEquals(r9, r)

    def test_format_wrongchar(self):
        self.assertRaises(ValueError, 'a%Zb'.__mod__, ((23,),))
class TestStringObject(testit.AppTestCase):

    def setUp(self):
        self.space = testit.objspace('std')

    def test_format_item(self):
        self.assertEquals('a23b', 'a%sb' % 23)
        self.assertEquals('23b', '%sb' % 23)
        self.assertEquals('a23', 'a%s' % 23)
        self.assertEquals('23', '%s' % 23)
        self.assertEquals('a%b', 'a%%b' % ())
        self.assertEquals('%b', '%%b' % ())
        self.assertEquals('a%', 'a%%' % ())
        self.assertEquals('%', '%%' % ())

    def test_format_wrongchar(self):
        self.assertRaises(ValueError, 'a%Zb'.__mod__, ((23,),))


if __name__ == '__main__':
    testit.main()
