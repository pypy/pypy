import py 
import sys

class TestInterpreter: 
    from pypy.interpreter.pycompiler import CPythonCompiler as CompilerClass

    def codetest(self, source, functionname, args):
        """Compile and run the given code string, and then call its function
        named by 'functionname' with arguments 'args'."""
        from pypy.interpreter import baseobjspace
        from pypy.interpreter import pyframe, gateway, module
        space = self.space

        source = str(py.code.Source(source).strip()) + '\n'

        w = space.wrap
        w_code = space.builtin.call('compile', 
                w(source), w('<string>'), w('exec'), w(0), w(0))

        tempmodule = module.Module(space, w("__temp__"))
        w_glob = tempmodule.w_dict
        space.setitem(w_glob, w("__builtins__"), space.builtin)

        code = space.unwrap(w_code)
        code.exec_code(space, w_glob, w_glob)

        wrappedargs = [w(a) for a in args]
        wrappedfunc = space.getitem(w_glob, w(functionname))
        try:
            w_output = space.call_function(wrappedfunc, *wrappedargs)
        except baseobjspace.OperationError, e:
            #e.print_detailed_traceback(space)
            return '<<<%s>>>' % e.errorstr(space)
        else:
            return space.unwrap(w_output)

    def setup_method(self, arg):
        ec = self.space.getexecutioncontext() 
        self.saved_compiler = ec.compiler
        ec.compiler = self.CompilerClass(self.space)

    def teardown_method(self, arg):
        ec = self.space.getexecutioncontext() 
        ec.compiler = self.saved_compiler

    def test_exception_trivial(self):
        x = self.codetest('''\
                def f():
                    try:
                        raise Exception()
                    except Exception, e:
                        return 1
                    return 2
            ''', 'f', [])
        assert x == 1

    def test_exception(self):
        x = self.codetest('''
            def f():
                try:
                    raise Exception, 1
                except Exception, e:
                    return e.args[0]
            ''', 'f', [])
        assert x == 1

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
        assert self.codetest(code, 'f', [0]) == -12
        assert self.codetest(code, 'f', [1]) == 1

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
        assert x == 5

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
        assert self.codetest(code, 'f', [2]) == 0
        assert self.codetest(code, 'f', [0]) == "infinite result"
        ess = "TypeError: unsupported operand type"
        res = self.codetest(code, 'f', ['x'])
        assert res.find(ess) >= 0
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
        assert self.codetest(code, 'f', [4]) == 1+2+3
        assert self.codetest(code, 'f', [9]) == 1+2+3+4

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
        assert self.codetest(code, 'f', [4]) == 1+2+3+400
        assert self.codetest(code, 'f', [9]) == (
                          1+2+3 + 5+6+7+8+900)

    def test_import(self):
        # Regression test for a bug in PyFrame.IMPORT_NAME: when an
        # import statement was executed in a function without a locals dict, a
        # plain unwrapped None could be passed into space.call_function causing
        # assertion errors later on.
        real_call_function = self.space.call_function
        def safe_call_function(w_obj, *arg_w):
            for arg in arg_w:
                assert arg is not None
            return real_call_function(w_obj, *arg_w)
        self.space.call_function = safe_call_function
        code = '''
            def f():
                import sys
            '''
        self.codetest(code, 'f', [])

    def test_extended_arg(self):
        longexpr = 'x = x or ' + '-x' * 2500
        code = '''
                def f(x):
                    %s
                    %s
                    %s
                    %s
                    %s
                    %s
                    %s
                    %s
                    %s
                    %s
                    while x:
                        x -= 1   # EXTENDED_ARG is for the JUMP_ABSOLUTE at the end of the loop
                    return x
                ''' % ((longexpr,)*10)
        assert self.codetest(code, 'f', [3]) == 0

    def test_call_star_starstar(self):
        code = '''\
            def f1(n):
                return n*2
            def f38(n):
                f = f1
                r = [
                    f(n, *[]),
                    f(n),
                    apply(f, (n,)),
                    apply(f, [n]),
                    f(*(n,)),
                    f(*[n]),
                    f(n=n),
                    f(**{'n': n}),
                    apply(f, (n,), {}),
                    apply(f, [n], {}),
                    f(*(n,), **{}),
                    f(*[n], **{}),
                    f(n, **{}),
                    f(n, *[], **{}),
                    f(n=n, **{}),
                    f(n=n, *[], **{}),
                    f(*(n,), **{}),
                    f(*[n], **{}),
                    f(*[], **{'n':n}),
                    ]
                return r
            '''
        assert self.codetest(code, 'f38', [117]) == [234]*19

    def test_star_arg(self):
        code = ''' 
            def f(x, *y):
                return y
            def g(u, v):
                return f(u, *v)
            '''
        assert self.codetest(code, 'g', [12, ()]) ==    ()
        assert self.codetest(code, 'g', [12, (3,4)]) == (3,4)
        assert self.codetest(code, 'g', [12, []]) ==    ()
        assert self.codetest(code, 'g', [12, [3,4]]) == (3,4)
        assert self.codetest(code, 'g', [12, {}]) ==    ()
        assert self.codetest(code, 'g', [12, {3:1}]) == (3,)

    def test_closure(self):
        code = '''
            def f(x, y):
                def g(u, v):
                    return u - v + 7*x
                return g
            def callme(x, u, v):
                return f(x, 123)(u, v)
            '''
        assert self.codetest(code, 'callme', [1, 2, 3]) == 6

    def test_list_comprehension(self):
        code = '''
            def f():
                return [dir() for i in [1]][0]
        '''
        assert self.codetest(code, 'f', [])[0] == '_[1]'

    def test_import_statement(self):
        for x in range(10):
            import os
        code = '''
            def f():
                for x in range(10):
                    import os
                return os.name
            '''
        assert self.codetest(code, 'f', []) == os.name


class TestPyPyInterpreter(TestInterpreter):
    """Runs the previous test with the pypy parser"""
    from pypy.interpreter.pycompiler import PythonAstCompiler as CompilerClass

    def test_extended_arg(self):
        py.test.skip("expression too large for the recursive parser")


class AppTestInterpreter: 
    def test_trivial(self):
        x = 42
        assert x == 42

    def test_trivial_call(self):
        def f(): return 42
        assert f() == 42

    def test_trivial_call2(self):
        def f(): return 1 + 1
        assert f() == 2

    def test_print(self):
        import sys
        save = sys.stdout 
        class Out(object):
            def __init__(self):
                self.args = []
            def write(self, *args):
                self.args.extend(args)
        out = Out()
        try:
            sys.stdout = out
            print 10
            assert out.args == ['10','\n']
        finally:
            sys.stdout = save

    def test_identity(self):
        def f(x): return x
        assert f(666) == 666
