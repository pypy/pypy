
class AppTestFfi:
    spaceconfig = dict(usemodules=['_rawffi', 'posix'])

    def test_exit(self):
        import posix, _rawffi
        if not hasattr(posix, 'fork'):
            skip("requires fork() to test")
        #
        pid = posix.fork()
        if pid == 0:
            _rawffi.exit(5)   # in the child
        pid, status = posix.waitpid(pid, 0)
        assert posix.WIFEXITED(status)
        assert posix.WEXITSTATUS(status) == 5
