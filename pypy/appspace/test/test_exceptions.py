import autopath
from pypy.tool import testit

class A(testit.AppTestCase):
    def test_import(self):
        import exceptions
        assert exceptions.SyntaxError is SyntaxError 

if __name__ == '__main__':
    testit.main()
