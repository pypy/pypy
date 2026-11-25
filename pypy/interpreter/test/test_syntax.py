from __future__ import with_statement
import py

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
        x
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
        x
        class g:
            x

    def f():
        exec "hi"
        x = 5
        class g:
            def h():
                x

    def f():
        from a import *
        x = 4
        class g:
            def h():
                x

    def f(x):
        exec "hi"
        x = 4
        class g:
            x

    def f(x):
        from a import *
        class g:
            x

    def f(x):
        exec "hi"
        x = 5
        class g:
            def h():
                x

    def f(x):
        from a import *
        x = 5
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
        except OperationError as e:
            if not e.match(space, space.w_SyntaxError):
                raise
        else:
            raise Exception("Should have raised SyntaxError")
    except:
        print '\n' + s
        raise


class AppTestSyntaxError:

    def test_tokenizer_error_location(self):
        line4 = "if ?: pass\n"
        try:
            exec "print\nprint\nprint\n" + line4
        except SyntaxError as e:
            assert e.lineno == 4
            assert e.text == line4
            assert e.offset == e.text.index('?') + 1
        else:
            raise Exception("no SyntaxError??")

    def test_grammar_error_location(self):
        try:
            exec """if 1:
                class Foo:
                    bla
                    a b c d e
                    bar
            """
        except SyntaxError as e:
            assert e.lineno == 4
            assert e.text.endswith('a b c d e\n')
            assert e.offset == e.text.index('b') + 1 # offset is 1-based
        else:
            raise Exception("no SyntaxError??")

    def test_astbuilder_error_location(self):
        program = "(1, 2) += (3, 4)\n"
        try:
            exec program
        except SyntaxError as e:
            assert e.lineno == 1
            assert e.text == program
        else:
            raise Exception("no SyntaxError??")

    def test_codegen_error_location(self):
        try:
            exec("if 1:\n     break")
        except SyntaxError as e:
            assert e.lineno == 2
            assert e.text == "     break"
            assert e.offset == 6

    def test_bad_encoding(self):
        program = """
# -*- coding: uft-8 -*-
pass
"""
        with raises(SyntaxError):
            exec program
