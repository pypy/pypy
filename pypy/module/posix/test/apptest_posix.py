import pytest

try:
    import posix as os
except ImportError:
    pytest.skip("only for posix")

if hasattr(os, "fork"):
    def test_register_at_fork():
        with pytest.raises(TypeError): # no args
            os.register_at_fork()
        with pytest.raises(TypeError): # positional args not supported
            os.register_at_fork(lambda : 1)
        with pytest.raises(TypeError): # not callable
            os.register_at_fork(before=1)

        # XXX this is unfortunately a small leak! all further tests that fork
        # will call these callbacks and append four ints to l
        l = [1]
        os.register_at_fork(
            before=lambda: l.append(2),
            after_in_parent=lambda: l.append(5),
            after_in_child=lambda: l.append(3))
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

