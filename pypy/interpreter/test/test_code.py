
import autopath
from pypy.tool import test 
import unittest


class AppTestCodeIntrospection(test.AppTestCase):
    def test_attributes(self):
        def f(): pass
        code = f.func_code    
        self.assert_(hasattr(code, 'co_code'))
        self.assert_(not hasattr(code,'__dict__'))
        self.assertEquals(code.co_name,'f')
        self.assertEquals(code.co_names,())
        self.assertEquals(code.co_varnames,())
        self.assertEquals(code.co_argcount,0)

if __name__ == '__main__':
    test.main()
