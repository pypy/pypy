# spaceconfig = {"usemodules": ["signal"]}
import sys


def test_wakeup_write_error_oserror_format():
    # When writing to the wakeup fd fails, the OSError should be formatted
    # as 'OSError: [Errno N] message', not just 'OSError: N'.
    import signal, os, io, errno
    if not hasattr(signal, 'SIGALRM'):
        skip('need SIGALRM')
    if not hasattr(signal, 'raise_signal'):
        skip('need signal.raise_signal')

    def handler(signum, frame):
        1/0

    signal.signal(signal.SIGALRM, handler)
    r, w = os.pipe()
    os.set_blocking(r, False)

    old_stderr = sys.stderr
    old_wakeup = signal.set_wakeup_fd(-1)
    sys.stderr = io.StringIO()
    signal.set_wakeup_fd(r)  # read-only end — writes will fail with EBADF
    try:
        try:
            signal.raise_signal(signal.SIGALRM)
        except ZeroDivisionError:
            pass
        err = sys.stderr.getvalue()
        assert '[Errno %d]' % errno.EBADF in err, (
            "Expected '[Errno %d]' in stderr, got: %r" % (errno.EBADF, err))
    finally:
        signal.set_wakeup_fd(old_wakeup)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        sys.stderr = old_stderr
        os.close(r)
        os.close(w)
