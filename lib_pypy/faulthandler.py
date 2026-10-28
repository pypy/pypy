# This is a dummy module imported for platforms where the built-in
# faulthandler module (which is implemented via vmprof) is not available.

import os
import signal
import sys


def _terminate(signum, code=3):
    # The debug helpers below are used by tests that need the process to
    # die abruptly, with the signal they name. Windows does not have the
    # signals.
    if sys.platform == 'win32':
        import _winapi
        _winapi.TerminateProcess(_winapi.GetCurrentProcess(), code)
    signal.raise_signal(signum)
    os.abort()      # only reached if signum was handled or ignored


def _read_null(*args, **kwargs):
    _terminate(signal.SIGSEGV)

def _sigsegv(*args, **kwargs):
    _terminate(signal.SIGSEGV)

def _sigfpe(*args, **kwargs):
    _terminate(signal.SIGFPE)

def _sigabrt(*args, **kwargs):
    _terminate(signal.SIGABRT)

def _stack_overflow(*args, **kwargs):
    _terminate(signal.SIGSEGV)


def enable(*args, **kwargs):
    pass

def disable(*args, **kwargs):
    pass

def is_enabled(*args, **kwargs):
    return False

def register(*args, **kwargs):
    pass

def cancel_dump_traceback_later(*args, **kwargs):
    pass

def unregister(*args, **kwargs):
    pass

try:
    import _thread
except ImportError:
    pass
else:
    # need the _thread module
    def dump_traceback_later(*args, **kwargs):
        pass

