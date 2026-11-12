"""Traceback dumps for test processes killed by the parallel test runner.

testrunner/runner.py SIGTERMs a test process that overruns --timeout, which
leaves no clue about where it was stuck.  When it sets PYPY_TEST_DUMP_DIR,
dump every thread's traceback there on that SIGTERM (and on a fatal signal);
the runner copies the file into the test's output.  Unrelated to
pypy/tool/watchdog.py, which kills a child that overruns a time limit.

It also opts in to being traced, so the runner can grab a C-level stack
before it kills us: a Python traceback stops at the ctypes call, which is no
help when the process is wedged inside a C library (Boehm's GC_malloc, say).

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
    except (IOError, OSError):
        return      # the directory went away
    try:
        faulthandler.enable(file=f)     # fatal signals: segfault, abort, ...
    except (AttributeError, RuntimeError, ValueError):
        f.close()
        return
    # keep the file alive: faulthandler holds its fd, not a reference to it
    _dumpfile = f
    try:
        # chain=False: chaining lets the default SIGTERM action kill us
        # mid-dump, so we get one frame.  The runner SIGKILLs 10s later.
        faulthandler.register(signal.SIGTERM, file=f, chain=False)
    except (AttributeError, RuntimeError, ValueError):
        pass        # register() needs sigaction, so it is absent on Windows;
                    # the fatal-signal dump above still works there
    _allow_ptrace()


def _allow_ptrace():
    """Let any process attach to us, so runner.py can grab a C stack.

    With yama ptrace_scope=1 (the usual default) only an ancestor may attach,
    and the gdb the runner spawns is our sibling.  PR_SET_PTRACER lifts that
    for this process only; it is a no-op where yama is not in use.
    """
    import sys
    if not sys.platform.startswith('linux'):
        return      # prctl is Linux-only; do not go dlsym'ing for it elsewhere
    try:
        import ctypes
        PR_SET_PTRACER = 0x59616d61
        PR_SET_PTRACER_ANY = ctypes.c_ulong(-1).value
        ctypes.CDLL(None).prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0)
    except Exception:
        pass        # not Linux, no ctypes, or prctl refused: C stacks are
                    # then simply unavailable, the Python dump still works
