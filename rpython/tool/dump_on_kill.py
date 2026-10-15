"""Traceback dumps for test processes killed by the parallel test runner.

testrunner/runner.py SIGTERMs a test process that overruns --timeout, which
leaves no clue about where it was stuck.  When it sets PYPY_TEST_DUMP_DIR,
dump every thread's traceback there on that SIGTERM (and on a fatal signal);
the runner copies the file into the test's output.  Unrelated to
pypy/tool/watchdog.py, which kills a child that overruns a time limit.

Two things this deliberately does not do: write to stderr, which pytest has
already redirected to its own capture file by the time conftest is imported,
so the dump would be lost; and use dump_traceback_later(), whose dump runs in
a separate thread while the interpreter keeps going -- on pypy2 that walk
crashes the process (SIGBUS, no output) when it fires during a busy test.
"""
import os

_dumpfile = None    # keep the fd alive for the handlers


def install():
    global _dumpfile
    dirname = os.environ.get('PYPY_TEST_DUMP_DIR')
    if not dirname or _dumpfile is not None:
        return
    try:
        import faulthandler
        import signal
    except ImportError:
        return      # not all hosts have it
    try:
        f = open(os.path.join(dirname, 'traceback-%d.txt' % os.getpid()), 'w')
        faulthandler.enable(file=f)     # fatal signals: segfault, abort, ...
        # chain=False: chaining lets the default SIGTERM action kill us
        # mid-dump, so we get one frame.  The runner SIGKILLs 10s later.
        faulthandler.register(signal.SIGTERM, file=f, chain=False)
    except (AttributeError, RuntimeError, ValueError, IOError, OSError):
        return      # partial implementation, or the directory went away
    _dumpfile = f
