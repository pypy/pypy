import autopath
from pypy.tool import testit


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

    def test_format_wrongchar(self):
        self.assertRaises(ValueError, 'a%Zb'.__mod__, ((23,),))


if __name__ == '__main__':
    testit.main()
