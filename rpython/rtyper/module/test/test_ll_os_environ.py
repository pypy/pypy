from rpython.translator.c.test.test_genc import compile
import os

def test_environ_items():
    def foo(x):
        if x:
            return len(os.environ.items())
        else:
            return 0

    f = compile(foo, [int], backendopt=False)
    assert f(1) > 0

def test_unset_error():
    def foo(x):
        if x:
            os.environ['TEST'] = 'STRING'
            assert os.environ['TEST'] == 'STRING'
            del os.environ['TEST']
            try:
                del os.environ['key=']
            except OSError:
                return 1
            return 2
        else:
            return 0

    f = compile(foo, [int], backendopt=False)
    assert f(1) == 1
