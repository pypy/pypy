import autopath
from pypy.tool import testit 

# this test isn't so much to test that the objspace interface *works*
# -- it's more to test that it's *there*

class TestTraceBackAttributes(testit.AppTestCase):

    def test_newstring(self):
        import sys
        def f():
            raise TypeError, "hello"

        def g():
            f()
        
        try:
            g()
        except:
            typ,val,tb = sys.exc_info()
        else:
            raise AssertionError, "should have raised"
        self.assert_(hasattr(tb, 'tb_frame'))
        self.assert_(hasattr(tb, 'tb_lasti'))
        self.assert_(hasattr(tb, 'tb_lineno'))
        self.assert_(hasattr(tb, 'tb_next'))

if __name__ == '__main__':
    testit.main()
