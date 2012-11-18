class AppTestSubprocess:
    spaceconfig = dict(usemodules=('_posixsubprocess',))

    # XXX write more tests

    def test_cloexec_pipe(self):
        import _posixsubprocess, os
        fd1, fd2 = _posixsubprocess.cloexec_pipe()
        # Sanity checks
        assert 0 <= fd1 < 4096
        assert 0 <= fd2 < 4096
        os.close(fd1)
        os.close(fd2)
