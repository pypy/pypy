import autopath
from pypy.tool import testit

class TestUserObject(testit.AppTestCase):
    def setUp(self):
        self.space = testit.objspace('std')

    def test_dictproxy(self):
        class NotEmpty:
            a = 1
        self.assertEquals(isinstance(NotEmpty.__dict__, dict), False)
        self.assert_('a' in NotEmpty.__dict__)
        self.assert_('a' in NotEmpty.__dict__.keys())
        self.assert_('b' not in NotEmpty.__dict__)
        self.assert_(isinstance(NotEmpty.__dict__.copy(), dict))
        self.assert_(NotEmpty.__dict__ == NotEmpty.__dict__.copy())
        try:
            NotEmpty.__dict__['b'] = 1
        except:
            pass
        else:
            raise AssertionError, 'this should not have been writable'

if __name__ == '__main__':
    testit.main()
