import testsupport

from pypy.objspace.std import StdObjSpace

class TestW_StdObjSpace(testsupport.TestCase):

    def setUp(self):
        self.space = StdObjSpace()

    def tearDown(self):
        pass

    def test_wrap_wrap(self):
        self.assertRaises(TypeError,
                          self.space.wrap,
                          self.space.wrap(0))


if __name__ == '__main__':
    testsupport.main()
