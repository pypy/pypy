# spaceconfig = {"usemodules":["sys"]}

def test_pypy_find_executable():
    # issue #4003
    import sys

    executable = sys.pypy_find_executable('*')
    if sys.platform == 'win32':
        assert executable.endswith('.exe')

        fake_executable = r'C:\Windows\System32\cmd.exe'  # should exist always
        assert executable == sys.pypy_find_executable(fake_executable)
    else:
        assert executable == ''
