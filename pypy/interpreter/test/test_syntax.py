import py
from pypy.conftest import gettestobjspace

def splitcases(s):
    lines = [line.rstrip() for line in s.split('\n')]
    s = '\n'.join(lines)
    result = []
    for case in s.split('\n\n'):
        if case.strip():
            result.append(str(py.code.Source(case))+'\n')
    return result


VALID = splitcases("""

    def f():
        def g():
            global x
            exec "hi"
            x

    def f():
        def g():
            global x
            from a import *
            x

    def f(x):
        def g():
            global x
            exec "hi"
            x

    def f(x):
        def g():
            global x
            from a import *
            x

    def f():
        def g():
            from a import *

    def f():
        def g():
            exec "hi"

    def f():
        from a import *

    def f():
        exec "hi"

    def f():
        from a import *
        def g():
            global x
            x

    def f():
        exec "hi"
        def g():
            global x
            x

    def f():
        from a import *
        def g(x):
            x

    def f():
        exec "hi"
        def g(x):
            x

    def f():
        from a import *
        lambda x: x

    def f():
        exec "hi"
        lambda x: x

    def f():
        from a import *
        x

    def f():
        exec "hi"
        x

    def f():
        from a import *
        (i for i in x)

    def f():
        exec "hi"
        (i for i in x)

    def f():
        class g:
            exec "hi"
            x

    def f():
        class g:
            from a import *
            x

""")

##    --- the following ones are valid in CPython, but not sensibly so:
##    --- if x is rebound, then it is even rebound in the parent scope!
##    def f(x):
##        class g:
##            from a import *
##            x
##    def f(x):
##        class g:
##            exec "x=41"
##            x

INVALID = splitcases("""

    def f():
        def g():
            exec "hi"
            x
    # NB. the above one is invalid in CPython, but there is no real reason

    def f(x):
        def g():
            exec "hi"
            x

    def f():
        def g():
            from a import *
            x
    # NB. the above one is invalid in CPython, but there is no real reason

    def f(x):
        def g():
            from a import *
            x

    def f():
        exec "hi"
        def g():
            x

    def f():
        exec "hi"
        lambda x: y

    def f():
        from a import *
        def g():
            x

    def f():
        from a import *
        lambda x: y

    def f():
        exec "hi"
        class g:
            x

    def f():
        from a import *
        class g:
            x

    def f():
        exec "hi"
        class g:
            def h():
                x

    def f():
        from a import *
        class g:
            def h():
                x

    def f(x):
        exec "hi"
        class g:
            x

    def f(x):
        from a import *
        class g:
            x

    def f(x):
        exec "hi"
        class g:
            def h():
                x

    def f(x):
        from a import *
        class g:
            def h():
                x

    def f():
        (i for i in x) = 10

    def f(x):
        def g():
            from a import *
            def k():
                return x

""")


for i in range(len(VALID)):
    exec """def test_valid_%d(space):
                checkvalid(space, %r)
""" % (i, VALID[i])

for i in range(len(INVALID)):
    exec """def test_invalid_%d(space):
                checkinvalid(space, %r)
""" % (i, INVALID[i])


def checkvalid(space, s):
    try:
        space.call_function(space.builtin.get('compile'),
                            space.wrap(s),
                            space.wrap('?'),
                            space.wrap('exec'))
    except:
        print '\n' + s
        raise

def checkinvalid(space, s):
    from pypy.interpreter.error import OperationError
    try:
        try:
            space.call_function(space.builtin.get('compile'),
                                space.wrap(s),
                                space.wrap('?'),
                                space.wrap('exec'))
        except OperationError, e:
            if not e.match(space, space.w_SyntaxError):
                raise
        else:
            raise Exception("Should have raised SyntaxError")
    except:
        print '\n' + s
        raise


class Py25AppTest:
    def setup_class(self):
        self.space = gettestobjspace(pyversion='2.5a')
        return

class AppTestCondExpr(Py25AppTest):
    def test_condexpr(self):
        for s, expected in [("x = 1 if True else 2", 1),
                            ("x = 1 if False else 2", 2)]:
            exec s
            assert x == expected

class AppTestWith(Py25AppTest):
    def test_with_simple(self):

        s = """from __future__ import with_statement
if 1:
        class Context:
            def __init__(self):
                self.calls = list()

            def __enter__(self):
                self.calls.append('__enter__')

            def __exit__(self, exc_type, exc_value, exc_tb):
                self.calls.append('__exit__')

        acontext = Context()
        with acontext:
            pass
        """
        exec s

        assert acontext.calls == '__enter__ __exit__'.split()

    def test_with_as_var(self):

        s = """from __future__ import with_statement
if 1:
        class Context:
            def __init__(self):
                self.calls = list()

            def __enter__(self):
                self.calls.append('__enter__')
                return self.calls

            def __exit__(self, exc_type, exc_value, exc_tb):
                self.calls.append('__exit__')
                self.exit_params = (exc_type, exc_value, exc_tb)

        acontextfact = Context()
        with acontextfact as avar:
            avar.append('__body__')
            pass
        """
        exec s

        assert acontextfact.exit_params == (None, None, None)
        assert acontextfact.calls == '__enter__ __body__ __exit__'.split()

    def test_with_raise_exception(self):

        s = """from __future__ import with_statement
if 1:
        class Context:
            def __init__(self):
                self.calls = list()

            def __enter__(self):
                self.calls.append('__enter__')
                return self.calls

            def __exit__(self, exc_type, exc_value, exc_tb):
                self.calls.append('__exit__')
                self.exit_params = (exc_type, exc_value, exc_tb)

        acontextfact = Context()
        error = RuntimeError('With Test')
        try:
            with acontextfact as avar:
                avar.append('__body__')
                raise error
                avar.append('__after_raise__')
        except RuntimeError:
            pass
        else:
            raise AssertionError('With did not raise RuntimeError')
        """
        exec s

        assert acontextfact.calls == '__enter__ __body__ __exit__'.split()
        assert acontextfact.exit_params[0:2] == (RuntimeError, error)
        import types
        assert isinstance(acontextfact.exit_params[2], types.TracebackType)

    def test_with_swallow_exception(self):

        s = """from __future__ import with_statement
if 1:
        class Context:
            def __init__(self):
                self.calls = list()

            def __enter__(self):
                self.calls.append('__enter__')
                return self.calls

            def __exit__(self, exc_type, exc_value, exc_tb):
                self.calls.append('__exit__')
                self.exit_params = (exc_type, exc_value, exc_tb)
                return True

        acontextfact = Context()
        error = RuntimeError('With Test')
        with acontextfact as avar:
            avar.append('__body__')
            raise error
            avar.append('__after_raise__')
        """
        exec s

        assert acontextfact.calls == '__enter__ __body__ __exit__'.split()
        assert acontextfact.exit_params[0:2] == (RuntimeError, error)
        import types
        assert isinstance(acontextfact.exit_params[2], types.TracebackType)

    def test_with_break(self):

        s = """from __future__ import with_statement
if 1:
        class Context:
            def __init__(self):
                self.calls = list()

            def __enter__(self):
                self.calls.append('__enter__')
                return self.calls

            def __exit__(self, exc_type, exc_value, exc_tb):
                self.calls.append('__exit__')
                self.exit_params = (exc_type, exc_value, exc_tb)

        acontextfact = Context()
        error = RuntimeError('With Test')
        for x in 1,:
            with acontextfact as avar:
                avar.append('__body__')
                break
                avar.append('__after_break__')
        else:
            raise AssertionError('Break failed with With, reached else clause')
        """
        exec s

        assert acontextfact.calls == '__enter__ __body__ __exit__'.split()
        assert acontextfact.exit_params == (None, None, None)

    def test_with_continue(self):

        s = """from __future__ import with_statement
if 1:
        class Context:
            def __init__(self):
                self.calls = list()

            def __enter__(self):
                self.calls.append('__enter__')
                return self.calls

            def __exit__(self, exc_type, exc_value, exc_tb):
                self.calls.append('__exit__')
                self.exit_params = (exc_type, exc_value, exc_tb)

        acontextfact = Context()
        error = RuntimeError('With Test')
        for x in 1,:
            with acontextfact as avar:
                avar.append('__body__')
                continue
                avar.append('__after_continue__')
        else:
            avar.append('__continue__')
        """
        exec s

        assert acontextfact.calls == '__enter__ __body__ __exit__ __continue__'.split()
        assert acontextfact.exit_params == (None, None, None)

    def test_with_return(self):
        s = """from __future__ import with_statement
if 1:
        class Context:
            def __init__(self):
                self.calls = list()

            def __enter__(self):
                self.calls.append('__enter__')
                return self.calls

            def __exit__(self, exc_type, exc_value, exc_tb):
                self.calls.append('__exit__')
                self.exit_params = (exc_type, exc_value, exc_tb)

        acontextfact = Context()
        error = RuntimeError('With Test')
        def g(acontextfact):
            with acontextfact as avar:
                avar.append('__body__')
                return '__return__'
                avar.append('__after_return__')
        acontextfact.calls.append(g(acontextfact))
        """
        exec s

        assert acontextfact.calls == '__enter__ __body__ __exit__ __return__'.split()
        assert acontextfact.exit_params == (None, None, None)

    def test_with_as_identifier(self):
        exec "with = 9"

    def test_with_as_keyword(self):
        try:
            exec "from __future__ import with_statement\nwith = 9"
        except SyntaxError:
            pass
        else:
            assert False, 'Assignment to with did not raise SyntaxError'

    def test_with_as_keyword_and_docstring(self):
        try:
            exec "'Docstring'\nfrom __future__ import with_statement\nwith = 9"
        except SyntaxError:
            pass
        else:
            assert False, 'Assignment to with did not raise SyntaxError'

    def test_with_as_keyword_compound(self):
        try:
            exec "from __future__ import generators, with_statement\nwith = 9"
        except SyntaxError:
            pass
        else:
            assert False, 'Assignment to with did not raise SyntaxError'

    def test_with_as_keyword_multiple(self):
        try:
            exec "from __future__ import generators\nfrom __future__ import with_statement\nwith = 9"
        except SyntaxError:
            pass
        else:
            assert False, 'Assignment to with did not raise SyntaxError'

    def test_as_as_identifier(self):
        exec "as = 9"
        exec "import sys as foo"

    def test_as_as_keyword(self):
        try:
            exec "from __future__ import with_statement\nas = 9"
        except SyntaxError:
            pass
        else:
            assert False, 'Assignment to as did not raise SyntaxError'

        exec "from __future__ import with_statement\nimport sys as foo"


    def test_with_propagate_compileflag(self):
        s = """from __future__ import with_statement
if 1:
        compile('''with x:
        pass''', '', 'exec')
        """
        exec s

if __name__ == '__main__':
    # only to check on top of CPython (you need 2.4)
    from py.test import raises
    for s in VALID:
        try:
            compile(s, '?', 'exec')
        except Exception, e:
            print '-'*20, 'FAILED TO COMPILE:', '-'*20
            print s
            print '%s: %s' % (e.__class__, e)
            print '-'*60
    for s in INVALID:
        try:
            raises(SyntaxError, compile, s, '?', 'exec')
        except Exception ,e:
            print '-'*20, 'UNEXPECTEDLY COMPILED:', '-'*20
            print s
            print '%s: %s' % (e.__class__, e)
            print '-'*60
