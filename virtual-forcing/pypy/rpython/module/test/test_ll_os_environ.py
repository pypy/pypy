from pypy.translator.c.test.test_genc import compile
import os

def test_environ_items():

    def foo(x):
        if x:
            return len(os.environ.items())
        else:
            return 0
    f = compile(foo, [int], backendopt=False)
    assert f(1) > 0
    
