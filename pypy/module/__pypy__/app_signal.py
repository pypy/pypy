import __pypy__.thread

class SignalsEnabled(object):
    '''A context manager to use in non-main threads:
enables receiving signals in a "with" statement.  More precisely, if a
signal is received by the process, then the signal handler might be
called either in the main thread (as usual) or within another thread
that is within a "with signals_enabled:".  This other thread should be
ready to handle unexpected exceptions that the signal handler might
raise --- notably KeyboardInterrupt.'''
    __enter__ = __pypy__.thread._signals_enter
    __exit__  = __pypy__.thread._signals_exit

signals_enabled = SignalsEnabled()
