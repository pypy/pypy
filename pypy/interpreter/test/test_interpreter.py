import py 
import sys
from pypy.interpreter import gateway, module, error

class TestInterpreter: 

    def codetest(self, source, functionname, args):
        """Compile and run the given code string, and then call its function
        named by 'functionname' with arguments 'args'."""
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
        except error.OperationError, e:
            #e.print_detailed_traceback(space)
            return '<<<%s>>>' % e.errorstr(space)
        else:
            return space.unwrap(w_output)

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

    def test_raise(self):
        x = self.codetest('''
            def f():
                raise 1
            ''', 'f', [])
        assert "TypeError:" in x
        assert ("exceptions must be old-style classes "
                "or derived from BaseException") in x

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
        res = self.codetest(code, 'f', ['x'])
        assert "TypeError:" in res
        assert "unsupported operand type" in res

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

    def test_import_default_arg(self):
        # CPython does not always call __import__() with 5 arguments,
        # but only if the 5th one is not -1.
        real_call_function = self.space.call_function
        space = self.space
        def safe_call_function(w_obj, *arg_w):
            assert not arg_w or not space.eq_w(arg_w[-1], space.wrap(-1))
            return real_call_function(w_obj, *arg_w)
        self.space.call_function = safe_call_function
        try:
            code = '''
                def f():
                    import sys
                '''
            self.codetest(code, 'f', [])
        finally:
            del self.space.call_function

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

    def test_print_unicode(self):
        import sys

        save = sys.stdout
        class Out(object):
            def __init__(self):
                self.data = []
            def write(self, x):
                self.data.append((type(x), x))
        sys.stdout = out = Out()
        try:
            print unichr(0xa2)
            assert out.data == [(unicode, unichr(0xa2)), (str, "\n")]
            out.data = []
            out.encoding = "cp424"     # ignored!
            print unichr(0xa2)
            assert out.data == [(unicode, unichr(0xa2)), (str, "\n")]
            del out.data[:]
            del out.encoding
            print u"foo\t", u"bar\n", u"trick", u"baz\n"  # softspace handling
            assert out.data == [(unicode, "foo\t"),
                                (unicode, "bar\n"),
                                (unicode, "trick"),
                                (str, " "),
                                (unicode, "baz\n"),
                                (str, "\n")]
        finally:
            sys.stdout = save

    def test_identity(self):
        def f(x): return x
        assert f(666) == 666

    def test_raise_recursion(self):
        def f(): f()
        try:
            f()
        except RuntimeError, e:
            assert str(e) == "maximum recursion depth exceeded"
        else:
            assert 0, "should have raised!"
