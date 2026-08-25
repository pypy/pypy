# spaceconfig = {"usemodules": ["_signal"]}
import pytest

try:
    import nt as posix
    _WIN32 = True
except ImportError:
    import posix
    _WIN32 = False
os = posix

if hasattr(os, "fork"):
    def test_register_at_fork():
        with pytest.raises(TypeError): # no args
            os.register_at_fork()
        with pytest.raises(TypeError): # positional args not supported
            os.register_at_fork(lambda : 1)
        with pytest.raises(TypeError): # not callable
            os.register_at_fork(before=1)
        with pytest.raises(TypeError): # wrong keyword
            os.register_at_fork(a=1)

        # XXX this is unfortunately a small leak! all further tests that fork
        # will call these callbacks and append four ints to l
        l = [1]
        os.register_at_fork(before=lambda: l.append(2))
        os.register_at_fork(after_in_parent=lambda: l.append(5))
        os.register_at_fork(after_in_child=lambda: l.append(3))
        def double_last():
            l[-1] *= 2
        os.register_at_fork(
            before=lambda: l.append(4),
            after_in_parent=lambda: l.append(-1),
            after_in_child=double_last)
        pid = os.fork()
        if pid == 0:   # child
            # l == [1, 4, 2, 6]
            os._exit(sum(l))

        assert l == [1, 4, 2, 5, -1]

        pid1, status1 = os.waitpid(pid, 0)
        assert pid1 == pid
        assert os.WIFEXITED(status1)
        res = os.WEXITSTATUS(status1)
        assert res == 13

    def test_fork_warns_when_threads_active():
        # avoid importing 'threading'/'warnings' (expensive untranslated):
        # use _thread directly, and register a minimal stand-in module
        # under sys.modules['warnings'] with just enough of the real
        # warnings module's interface (_showwarnmsg + WarningMessage) for
        # _warnings.warn() to report through instead of writing to stderr.
        import _thread
        import _warnings
        import _signal
        import sys
        import time

        # fork()+threads is inherently hang-prone (that's the whole point
        # of the warning under test); bound the worst case so a stuck run
        # fails loudly instead of hanging the rest of the test suite.
        def on_alarm(sig, frame):
            raise RuntimeError("test_fork_warns_when_threads_active timed out")
        old_alarm_handler = _signal.signal(_signal.SIGALRM, on_alarm)
        _signal.alarm(10)
        try:
            ready = _thread.allocate_lock()
            ready.acquire()
            stop = []
            def background_thread():
                ready.release()
                # bounded (~5s) so it self-terminates even if something odd
                # happens to thread scheduling around the fork() below
                for _ in range(500):
                    if stop:
                        break
                    time.sleep(0.01)

            _thread.start_new(background_thread, ())
            ready.acquire()  # wait until the thread actually started

            class FakeWarningMessage:
                def __init__(self, message, category, filename, lineno,
                             file=None, line=None, source=None):
                    self.message = message
                    self.category = category

            captured = []
            class FakeWarningsModule:
                WarningMessage = FakeWarningMessage
                def _showwarnmsg(self, msg):
                    captured.append(msg)

            old_filters = _warnings.filters[:]
            old_warnings_mod = sys.modules.get('warnings')
            sys.modules['warnings'] = FakeWarningsModule()
            _warnings.filters.insert(0, ('always', None, DeprecationWarning, None, 0))
            _warnings._filters_mutated()
            try:
                pid = os.fork()
                if pid == 0:
                    os._exit(0)
            finally:
                if old_warnings_mod is not None:
                    sys.modules['warnings'] = old_warnings_mod
                else:
                    del sys.modules['warnings']
                _warnings.filters[:] = old_filters
                _warnings._filters_mutated()
                stop.append(1)

            assert len(captured) == 1
            assert captured[0].category is DeprecationWarning
            assert 'fork' in str(captured[0].message)
            os.waitpid(pid, 0)
        finally:
            _signal.alarm(0)
            _signal.signal(_signal.SIGALRM, old_alarm_handler)


def test_cpu_count():
    cc = posix.cpu_count()
    assert cc is None or (isinstance(cc, int) and cc > 0)

def test_putenv_invalid_name():
    with pytest.raises(ValueError):
        posix.putenv("foo=bar", "xxx")

if not _WIN32:
    def test_all_pathconf_defined():
        import sys
        import posix
        try:
            fd = sys.stdin.fileno()
        except ValueError:
            # translated test run with a fake sys.stdin with no fileno
            fd = 1
        for name in posix.pathconf_names:
            posix.fpathconf(fd, name) # does not crash

if _WIN32:
    def test__supports_virtual_terminal():
        import sys
        isatty = os.isatty(sys.stderr.fileno())
        assert os._supports_virtual_terminal() == isatty

    def test__getdiskusage():
        import nt
        total, free = nt._getdiskusage(nt.getcwd())
        assert isinstance(total, int)
        assert isinstance(free, int)
        assert total > 0
        assert free >= 0
        assert free <= total

    def test__getfinalpathname_bytes():
        import nt
        path = nt.getcwd().encode()
        result = nt._getfinalpathname(path)
        assert isinstance(result, bytes)
        prefix = b'\\\\?\\'
        stripped = result[len(prefix):] if result.startswith(prefix) else result
        assert stripped.lower() == path.lower()
