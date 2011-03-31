import os

if hasattr(os, 'wait3'):
    def test_os_wait3():
        exit_status = 0x33

        if not hasattr(os, "fork"):
            skip("Need fork() to test wait3()")

        child = os.fork()
        if child == 0: # in child
            os._exit(exit_status)
        else:
            pid, status, rusage = os.wait3(0)
            assert child == pid
            assert os.WIFEXITED(status)
            assert os.WEXITSTATUS(status) == exit_status
            assert isinstance(rusage.ru_utime, float)
            assert isinstance(rusage.ru_maxrss, int)
