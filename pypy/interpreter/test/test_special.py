
import autopath 
from pypy.tool import testit 

class SpecialTestCase(testit.AppTestCase):
    def test_Ellipsis(self):
        self.assertEquals(Ellipsis, Ellipsis)
        self.assertEquals(repr(Ellipsis), 'Ellipsis')
    
    def test_NotImplemented(self):
        def f():
            return NotImplemented
        self.assertEquals(f(), NotImplemented) 
        self.assertEquals(repr(NotImplemented), 'NotImplemented')

if __name__ == '__main__':
    testit.main()

