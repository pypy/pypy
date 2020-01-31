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


