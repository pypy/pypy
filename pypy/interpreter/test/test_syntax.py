from __future__ import with_statement
import py
import commands
import pypy.conftest

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
            exec("hi")
            x

    def f(x):
        def g():
            global x
            exec("hi")
            x

    def f():
        def g():
            exec("hi")

    def f():
        exec("hi")

    def f():
        exec("hi")
        def g():
            global x
            x

    def f():
        exec("hi")
        def g(x):
            x

    def f():
        exec("hi")
        lambda x: x

    def f():
        exec("hi")
        x

    def f():
        exec("hi")
        (i for i in x)

    def f():
        class g:
            exec("hi")
            x

""")

##    --- the following one is valid in CPython, but not sensibly so:
##    --- if x is rebound, then it is even rebound in the parent scope!
##    def f(x):
##        class g:
##            exec "x=41"
##            x

INVALID = splitcases("""

    def f():
        from x import *

    def f():
        (i for i in x) = 10

    async def foo(a=await something()):
        pass

    async def foo():
        await

    def foo():
        await something()

    async def foo():
        yield from []

    async def foo():
        await await fut

    async def foo():
        yield
        return 42

    async def foo():
        return (yield 1)

    async def foo():
        if a:
            return 42
        yield

""")


for i in range(len(VALID)):
    exec """def test_valid_%d(space, tmpdir):
                checkvalid_cpython(tmpdir, %d, %r)
                checkvalid(space, %r)
""" % (i, i, VALID[i], VALID[i])

for i in range(len(INVALID)):
    exec """def test_invalid_%d(space, tmpdir):
                checkinvalid_cpython(tmpdir, %d, %r)
                checkinvalid(space, %r)
""" % (i, i, INVALID[i], INVALID[i])


def checksyntax_cpython(tmpdir, i, s):
    python3 = pypy.conftest.option.python
    if python3 is None:
        print 'Warning: cannot run python3 to check syntax'
        return

    src = '''
try:
    exec("""%s
""")
except SyntaxError as e:
    print(e)
    raise SystemExit(1)
else:
    print('OK')
''' % s
    pyfile = tmpdir.join('checkvalid_%d.py' % i)
    pyfile.write(src)
    res = commands.getoutput('"%s" "%s"' % (python3, pyfile))
    return res

def checkvalid_cpython(tmpdir, i, s):
    res = checksyntax_cpython(tmpdir, i, s)
    if res is not None and res != 'OK':
        print s
        print
        print res
        assert False, 'checkvalid_cpython failed'

def checkinvalid_cpython(tmpdir, i, s):
    res = checksyntax_cpython(tmpdir, i, s)
    if res is not None and res == 'OK':
        print s
        print
        print res
        assert False, 'checkinvalid_cpython failed, did not raise SyntaxError'


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
        except OperationError as e:
            if not e.match(space, space.w_SyntaxError):
                raise
        else:
            raise Exception("Should have raised SyntaxError")
    except:
        print '\n' + s
        raise


class AppTestSyntaxError:

    def test_bad_encoding(self):
        '''
        program = """
# -*- coding: uft-8 -*-
pass
"""
        with raises(SyntaxError):
            exec(program)
        '''

