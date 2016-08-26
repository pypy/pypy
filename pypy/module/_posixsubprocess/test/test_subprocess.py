from os.path import dirname

class AppTestSubprocess:
    spaceconfig = dict(usemodules=('_posixsubprocess', 'signal',
                                   'fcntl', 'select', 'time', 'struct'))
    # XXX write more tests

    def setup_class(cls):
        cls.w_dir = cls.space.wrap(dirname(__file__))

    def test_cloexec_pipe(self):
        import _posixsubprocess, os
        fd1, fd2 = _posixsubprocess.cloexec_pipe()
        # Sanity checks
        assert 0 <= fd1 < 4096
        assert 0 <= fd2 < 4096
        os.close(fd1)
        os.close(fd2)

    def test_close_fds_true(self):
        import traceback  # Work around a recursion limit
        import subprocess
        import os.path
        import os

        fds = os.pipe()
        #self.addCleanup(os.close, fds[0])
        #self.addCleanup(os.close, fds[1])

        open_fds = set(fds)
        # add a bunch more fds
        for _ in range(9):
            fd = os.open("/dev/null", os.O_RDONLY)
            #self.addCleanup(os.close, fd)
            open_fds.add(fd)

        p = subprocess.Popen(['/usr/bin/env', 'python', os.path.join(self.dir, 'fd_status.py')], stdout=subprocess.PIPE, close_fds=True)
        output, ignored = p.communicate()
        remaining_fds = set(map(int, output.split(b',')))

        assert not (remaining_fds & open_fds), "Some fds were left open"
        assert 1 in remaining_fds, "Subprocess failed"

    def test_start_new_session(self):
        # For code coverage of calling setsid().  We don't care if we get an
        # EPERM error from it depending on the test execution environment, that
        # still indicates that it was called.
        import traceback  # Work around a recursion limit
        import subprocess
        import os
        try:
            output = subprocess.check_output(
                    ['/usr/bin/env', 'python', "-c",
                     "import os; print(os.getpgid(os.getpid()))"],
                    start_new_session=True)
        except OSError as e:
            if e.errno != errno.EPERM:
                raise
        else:
            parent_pgid = os.getpgid(os.getpid())
            child_pgid = int(output)
            assert parent_pgid != child_pgid

    def test_cpython_issue15736(self):
        import _posixsubprocess
        import sys
        n = 0
        class Z(object):
            def __len__(self):
                return sys.maxsize + n
            def __getitem__(self, i):
                return b'x'
        raises(MemoryError, _posixsubprocess.fork_exec,
               1,Z(),3,[1, 2],5,6,7,8,9,10,11,12,13,14,15,16,17)
        n = 1
        raises(OverflowError, _posixsubprocess.fork_exec,
               1,Z(),3,[1, 2],5,6,7,8,9,10,11,12,13,14,15,16,17)

    def test_pass_fds_make_inheritable(self):
        import subprocess, posix

        fd1, fd2 = posix.pipe()
        assert posix.get_inheritable(fd1) is False
        assert posix.get_inheritable(fd2) is False

        subprocess.check_call(['/usr/bin/env', 'python', '-c',
                               'import os;os.write(%d,b"K")' % fd2],
                              close_fds=True, pass_fds=[fd2])
        res = posix.read(fd1, 1)
        assert res == b"K"
        posix.close(fd1)
        posix.close(fd2)
