# derived from test_random_things.py
import py
from ctypes import *
import sys

def callback_func(arg):
    42 / arg
    raise ValueError(arg)

class TestCallbackTraceback:
    # When an exception is raised in a ctypes callback function, the C
    # code prints a traceback.
    #
    # This test makes sure the exception types *and* the exception
    # value is printed correctly.
    #
    # Changed in 0.9.3: No longer is '(in callback)' prepended to the
    # error message - instead a additional frame for the C code is
    # created, then a full traceback printed.  When SystemExit is
    # raised in a callback function, the interpreter exits.

    def capture_stderr(self, func, *args, **kw):
        # helper - call function 'func', and return the captured stderr
        import StringIO
        old_stderr = sys.stderr
        logger = sys.stderr = StringIO.StringIO()
        try:
            func(*args, **kw)
        finally:
            sys.stderr = old_stderr
        return logger.getvalue()

    def test_ValueError(self):
        cb = CFUNCTYPE(c_int, c_int)(callback_func)
        out = self.capture_stderr(cb, 42)
        assert out.splitlines()[-1] == (
                             "ValueError: 42")

    def test_IntegerDivisionError(self):
        cb = CFUNCTYPE(c_int, c_int)(callback_func)
        out = self.capture_stderr(cb, 0)
        assert out.splitlines()[-1][:19] == (
                             "ZeroDivisionError: ")

    def test_FloatDivisionError(self):
        cb = CFUNCTYPE(c_int, c_double)(callback_func)
        out = self.capture_stderr(cb, 0.0)
        assert out.splitlines()[-1][:19] == (
                             "ZeroDivisionError: ")

    def test_TypeErrorDivisionError(self):
        cb = CFUNCTYPE(c_int, c_char_p)(callback_func)
        out = self.capture_stderr(cb, "spam")
        assert out.splitlines()[-1].startswith(
                             "TypeError: "
                             "unsupported operand type(s) for")

    def test_SystemExit(self):
        import _rawffi
        if sys.flags.inspect:
            skip("requires sys.flags.inspect == 0")
        def callback_func(arg):
            raise SystemExit(42)
        def custom_exit(value):
            raise Exception("<<<exit(%r)>>>" % (value,))
        original_exit = _rawffi.exit
        try:
            _rawffi.exit = custom_exit
            #
            cb = CFUNCTYPE(c_int, c_int)(callback_func)
            cb2 = cast(cast(cb, c_void_p), CFUNCTYPE(c_int, c_int))
            out = self.capture_stderr(cb2, 0)
            assert out.splitlines()[-1] == "Exception: <<<exit(42)>>>"
            #
            cb = CFUNCTYPE(c_int, c_int)(callback_func)
            out = self.capture_stderr(cb, 0)
            assert out.splitlines()[-1] == "Exception: <<<exit(42)>>>"
            #
        finally:
            _rawffi.exit = original_exit
