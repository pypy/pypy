import py
from pypy.translator.cl.buildcl import make_cl_func

def test_handle_exception():
    py.test.skip("TODO")
    class MyException(Exception):
        pass
    def raise_exception():
        # This is in a separate function to fool RTyper
        raise MyException()
    def handle_exception(flag):
        try:
            if flag:
                raise_exception()
            else:
                return 2
        except MyException:
            return 1
    cl_handle_exception = make_cl_func(handle_exception, [bool])
    assert cl_handle_exception(True) == 1
    assert cl_handle_exception(False) == 2
