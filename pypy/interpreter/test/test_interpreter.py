import autopath
from pypy.tool import test

class TestInterpreter(test.TestCase):

    def codetest(self, source, functionname, args):
        """Compile and run the given code string, and then call its function
        named by 'functionname' with arguments 'args'."""
        from pypy.interpreter import baseobjspace, executioncontext
        from pypy.interpreter import pyframe, gateway, module
        space = self.space

        compile = space.builtin.compile
        w = space.wrap
        w_code = compile(w(source), w('<string>'), w('exec'), w(0), w(0))

        ec = executioncontext.ExecutionContext(space)

        tempmodule = module.Module(space, w("__temp__"))
        w_glob = tempmodule.w_dict
        space.setitem(w_glob, w("__builtins__"), space.w_builtins)

        code = space.unwrap(w_code)
        code.exec_code(space, w_glob, w_glob)

        wrappedargs = w(args)
        wrappedfunc = space.getitem(w_glob, w(functionname))
        wrappedkwds = space.newdict([])
        try:
            w_output = space.call(wrappedfunc, wrappedargs, wrappedkwds)
        except baseobjspace.OperationError, e:
            #e.print_detailed_traceback(space)
            return '<<<%s>>>' % e.errorstr(space)
        else:
            return space.unwrap(w_output)

    def setUp(self):
        self.space = test.objspace()

    def test_exception_trivial(self):
        x = self.codetest('''
def f():
    try:
        raise Exception()
    except Exception, e:
        return 1
    return 2
''', 'f', [])
        self.assertEquals(x, 1)

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
        a = -12
    finally:
        return a
'''
        self.assertEquals(self.codetest(code, 'f', [0]), -12)
        self.assertEquals(self.codetest(code, 'f', [1]), 1)

##     def test_raise(self):
##         x = self.codetest('''
## def f():
##     raise 1
## ''', 'f', [])
##         self.assertEquals(x, '<<<TypeError: exceptions must be instances or subclasses of Exception or strings (deprecated), not int>>>')

    def test_except2(self):
        x = self.codetest('''
def f():
    try:
        z = 0
        try:
            "x"+1
        except TypeError, e:
            z = 5
            raise e
    except TypeError:
        return z
''', 'f', [])
        self.assertEquals(x, 5)

    def test_except3(self):
        code = '''
def f(v):
    z = 0
    try:
        z = 1//v
    except ZeroDivisionError, e:
        z = "infinite result"
    return z
'''
        self.assertEquals(self.codetest(code, 'f', [2]), 0)
        self.assertEquals(self.codetest(code, 'f', [0]), "infinite result")
        ess = "TypeError: unsupported operand type"
        res = self.codetest(code, 'f', ['x'])
        self.failUnless(res.find(ess) >= 0)
        # the following (original) test was a bit too strict...:
        # self.assertEquals(self.codetest(code, 'f', ['x']), "<<<TypeError: unsupported operand type(s) for //: 'int' and 'str'>>>")

    def test_break(self):
        code = '''
def f(n):
    total = 0
    for i in range(n):
        try:
            if i == 4:
                break
        finally:
            total += i
    return total
'''
        self.assertEquals(self.codetest(code, 'f', [4]), 1+2+3)
        self.assertEquals(self.codetest(code, 'f', [9]), 1+2+3+4)

    def test_continue(self):
        code = '''
def f(n):
    total = 0
    for i in range(n):
        try:
            if i == 4:
                continue
        finally:
            total += 100
        total += i
    return total
'''
        self.assertEquals(self.codetest(code, 'f', [4]), 1+2+3+400)
        self.assertEquals(self.codetest(code, 'f', [9]),
                          1+2+3 + 5+6+7+8+900)

class AppTestInterpreter(test.AppTestCase):
    def test_exception(self):
        try:
            raise Exception, 1
        except Exception, e:
            self.assertEquals(e.args[0], 1)

    def test_trivial(self):
        x = 42
        self.assertEquals(x, 42)

    def test_raise(self):
        def f():
            raise Exception
        self.assertRaises(Exception, f)

    def test_exception(self):
        try:
            raise Exception
            self.fail("exception failed to raise")
        except:
            pass
        else:
            self.fail("exception executing else clause!")

    def test_raise2(self):
        def f(r):
            try:
                raise r
            except LookupError:
                return 1
        self.assertRaises(Exception, f, Exception)
        self.assertEquals(f(IndexError), 1)

    def test_raise3(self):
        try:
            raise 1
        except TypeError:
            pass
        else:
            self.fail("shouldn't be able to raise 1")

    def test_trivial_call(self):
        def f(): return 42
        self.assertEquals(f(), 42)

    def test_trivial_call2(self):
        def f(): return 1 + 1
        self.assertEquals(f(), 2)

    def test_print(self):
        import sys
        save = sys.stdout 
        class Out:
            def __init__(self):
                self.args = []
            def write(self, *args):
                self.args.extend(args)
        out = Out()
        try:
            sys.stdout = out
            print 10
            self.assertEquals(out.args, ['10','\n'])
        finally:
            sys.stdout = save

    def test_identity(self):
        def f(x): return x
        self.assertEquals(f(666), 666)


if __name__ == '__main__':
    test.main()
