
import autopath
from pypy.tool import testit 
import unittest


class AppTestCodeIntrospection(testit.AppTestCase):
    def test_attributes(self):
        def f(): pass
        code = f.func_code    
        self.assert_(hasattr(code, 'co_code'))
        self.assert_(hasattr(code, '__class__'))
        self.assert_(not hasattr(code,'__dict__'))
        self.assertEquals(code.co_name,'f')
        self.assertEquals(code.co_names,())
        self.assertEquals(code.co_varnames,())
        self.assertEquals(code.co_argcount,0)
    def test_code(self):
        import new
        codestr = "global c\na = 1\nb = 2\nc = a + b\n"
        ccode = compile(codestr, '<string>', 'exec')
        co = new.code(ccode.co_argcount,
                      ccode.co_nlocals,
                      ccode.co_stacksize,
                      ccode.co_flags,
                      ccode.co_code,
                      ccode.co_consts,
                      ccode.co_names,
                      ccode.co_varnames,
                      ccode.co_filename,
                      ccode.co_name,
                      ccode.co_firstlineno,
                      ccode.co_lnotab,
                      ccode.co_freevars,
                      ccode.co_cellvars)
        d = {}
        exec co in d
        self.assertEquals(d['c'], 3)
        # test backwards-compatibility version with no freevars or cellvars
        co = new.code(ccode.co_argcount,
                      ccode.co_nlocals,
                      ccode.co_stacksize,
                      ccode.co_flags,
                      ccode.co_code,
                      ccode.co_consts,
                      ccode.co_names,
                      ccode.co_varnames,
                      ccode.co_filename,
                      ccode.co_name,
                      ccode.co_firstlineno,
                      ccode.co_lnotab)
        d = {}
        exec co in d
        self.assertEquals(d['c'], 3)

if __name__ == '__main__':
    testit.main()
