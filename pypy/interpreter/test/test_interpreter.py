import unittest
import support

class TestInterpreter(unittest.TestCase):

    def codetest(self, code, functionname, args):
        """Compile and run the given code string, and then call its function
        named by 'functionname' with arguments 'args'."""
        from pypy.interpreter import baseobjspace, executioncontext, appfile

        bytecode = executioncontext.inlinecompile(code)
        apphelper = appfile.AppHelper(self.space, bytecode)

        wrappedargs = [self.space.wrap(arg) for arg in args]
        try:
            w_output = apphelper.call(functionname, wrappedargs)
        except baseobjspace.OperationError, e:
            e.print_detailed_traceback(self.space)
            return '<<<%s>>>' % e.errorstr(self.space)
        else:
            return self.space.unwrap(w_output)

    def setUp(self):
        from pypy.objspace.trivial import TrivialObjSpace
        self.space = TrivialObjSpace()

    def test_trivial(self):
        x = self.codetest('''
def g(): return 42''', 'g', [])
        self.assertEquals(x, 42)

    def test_trivial_call(self):
        x = self.codetest('''
def f(): return 42
def g(): return f()''', 'g', [])
        self.assertEquals(x, 42)

    def test_trivial_call2(self):
        x = self.codetest('''
def f(): return 1 + 1
def g(): return f()''', 'g', [])
        self.assertEquals(x, 2)

    def test_print(self):
        x = self.codetest('''
def g(): print 10''', 'g', [])
        self.assertEquals(x, None)

    def test_identity(self):
        x = self.codetest('''
def g(x): return x''', 'g', [666])
        self.assertEquals(x, 666)

    def test_exception(self):
        x = self.codetest('''
def f():
    try:
        raise Exception, 1
    except Exception, e:
        return e.args[0]
''', 'f', [])
        self.assertEquals(x, 1)

    def test_finally(self):
        code = '''
def f(a):
    try:
        if a:
            raise Exception
    finally:
        return 2
'''
        self.assertEquals(self.codetest(code, 'f', [0]), 2)
        self.assertEquals(self.codetest(code, 'f', [1]), 2)

    def test_raise(self):
        x = self.codetest('''
def f():
    raise 1
''', 'f', [])
        self.assertEquals(x, '<<<TypeError: exceptions must be classes, instances, or strings (deprecated), not int>>>')


if __name__ == '__main__':
    unittest.main()
