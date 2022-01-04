import pytest

try:
    import nt as posix
except ImportError:
    import posix
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

    def test_fork_hook_creates_thread_bug():
        import threading
        def daemon():
            while 1:
                time.sleep(10)

        daemon_thread = None
        def create_thread():
            nonlocal daemon_thread
            daemon_thread = threading.Thread(name="b", target=daemon, daemon=True)
            daemon_thread.start()

        os.register_at_fork(after_in_child=create_thread)
        pid = os.fork()
        if pid == 0:   # child
            os._exit(daemon_thread._ident in threading._active)

        pid1, status1 = os.waitpid(pid, 0)
        assert status1


def test_cpu_count():
    cc = posix.cpu_count()
    assert cc is None or (isinstance(cc, int) and cc > 0)

def test_putenv_invalid_name():
    with pytest.raises(ValueError):
        posix.putenv("foo=bar", "xxx")
