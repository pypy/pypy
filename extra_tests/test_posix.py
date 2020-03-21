# Tests variant functions which also accept file descriptors,
# dir_fd and follow_symlinks.
def test_have_functions():
    import os
    assert os.stat in os.supports_fd  # fstat() is supported everywhere
    if os.name != 'nt':
        assert os.chdir in os.supports_fd  # fchdir()
    else:
        assert os.chdir not in os.supports_fd
    if os.name == 'posix':
        assert os.open in os.supports_dir_fd  # openat()

def test_popen():
    import os
    for i in range(5):
        stream = os.popen('echo 1')
        res = stream.read()
        assert res == '1\n'
        assert stream.close() is None

def test_popen_with():
    import os
    stream = os.popen('echo 1')
    with stream as fp:
        res = fp.read()
        assert res == '1\n'

def test_pickle():
    import pickle
    import os
    st = os.stat('.')
    # print(type(st).__module__)
    s = pickle.dumps(st)
    # print(repr(s))
    new = pickle.loads(s)
    assert new == st
    assert type(new) is type(st)


