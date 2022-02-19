# spaceconfig = {"usemodules": ["_posixsubprocess", "signal", "fcntl", "select", "time", "struct"]}
import pytest

_posixsubprocess = pytest.importorskip('_posixsubprocess')

from os.path import dirname
import traceback  # Work around a recursion limit
import subprocess
import os
import posix

directory = dirname(__file__)

# XXX write more tests

def test_close_fds_true():
    fds = os.pipe()

    open_fds = set(fds)
    # add a bunch more fds
    for _ in range(9):
        fd = os.open("/dev/null", os.O_RDONLY)
        open_fds.add(fd)

    p = subprocess.Popen(['/usr/bin/env', 'python', os.path.join(directory, 'fd_status.py')], stdout=subprocess.PIPE, close_fds=True)
    output, ignored = p.communicate()
    remaining_fds = set(map(int, output.split(b',')))

    assert not (remaining_fds & open_fds), "Some fds were left open"
    assert 1 in remaining_fds, "Subprocess failed"

def test_start_new_session():
    # For code coverage of calling setsid().  We don't care if we get an
    # EPERM error from it depending on the test execution environment, that
    # still indicates that it was called.
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

def test_cpython_issue15736():
    n = 0
    class Z(object):
        def __len__(self):
            import sys
            return sys.maxsize + n
        def __getitem__(self, i):
            return b'x'
    raises(MemoryError, _posixsubprocess.fork_exec,
           1,Z(),3,(1, 2),5,6,7,8,9,10,11,12,13,14,15,16,17)
    n = 1
    raises(OverflowError, _posixsubprocess.fork_exec,
           1,Z(),3,(1, 2),5,6,7,8,9,10,11,12,13,14,15,16,17)

def test_pass_fds_make_inheritable():
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


def test_issue_3630():
    import time
    # Make sure the registered callback functions are not called unless
    # fork_exec has a preexec_fn

    tmpfile = 'fork_exec.txt'
    with open(tmpfile, 'w'):
        pass


    # from multiprocessing.util.py
    def spawnv_passfds(path, args, passfds, preexec_fn=None):
        passfds = tuple(sorted(map(int, fds_to_pass)))
        errpipe_read, errpipe_write = os.pipe()
        try:
            return _posixsubprocess.fork_exec(
                args, [os.fsencode(path)], True, passfds, None, None,
                -1, -1, -1, -1, -1, -1, errpipe_read, errpipe_write,
                False, False, preexec_fn)
        finally:
            os.close(errpipe_read)
            os.close(errpipe_write)

    def preexec_fn():
        pass
    
    def before():
        with open(tmpfile, mode='a') as fid:
            fid.write('before\n')
        print('before hook done')

    def parent():
        print('parent hook')
        for i in range(10):
            time.sleep(0.1)
            with open(tmpfile, mode='r') as fid:
                if 'child' in fid.read():
                    break
        else:
            print('tmpfile not updated')
        with open(tmpfile, mode='a') as fid:
            fid.write('parent\n')
        print('parent hook done')

    def child():
        with open(tmpfile, mode='a') as fid:
            fid.write('child\n')
        print('child hook done')

    os.register_at_fork(before=before, after_in_parent=parent, after_in_child=child)
    fds_to_pass = []
    try:
        fds_to_pass.append(sys.stderr.fileno())
    except Exception:
        pass
    
    r, w = os.pipe()
    fds_to_pass.append(r)
    args = ['ls', '.']
    
    try:
        spawnv_passfds('ls', args, fds_to_pass)
        with open(tmpfile, mode='r') as fid:
            contents = fid.read()
        assert len(contents) == 0

        spawnv_passfds('ls', args, fds_to_pass, preexec_fn=preexec_fn)
        with open(tmpfile, mode='r') as fid:
            contents = fid.read()
        assert 'child' in contents
        assert 'parent' in contents
        assert 'before' in contents
    finally:
        os.remove(tmpfile)
        
