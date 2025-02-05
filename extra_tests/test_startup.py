import signal
import time
import os
import subprocess
import sys

def test_platform_not_imported():
    import subprocess
    out = subprocess.check_output([sys.executable, '-c',
         'import sys; print(list(sys.modules.keys()))'], universal_newlines=True)
    modules = [x.strip(' "\'') for x in out.strip().strip('[]').split(',')]
    assert 'platform' not in modules
    assert 'threading' not in modules


def test_executable_win32():
    # issue #4003
    import os
    import sys

    out = subprocess.check_output([r'*', '-c',
         'import sys; print (repr(sys.executable))'], universal_newlines=True, executable=sys.executable)
    if sys.platform == 'win32':
        assert out.strip() == repr(sys.executable)

        fake_executable = r'C:\Windows\System32\cmd.exe'
        assert os.path.isfile(fake_executable)  # should exist always
        out = subprocess.check_output([fake_executable, '-c',
            'import sys; print (repr(sys.executable))'], universal_newlines=True, executable=sys.executable)
        assert out.strip() == repr(sys.executable)
    else:
        assert out.strip() == repr('')


def test_ctrl_c_causes_atexit():
    process = subprocess.Popen(
            [sys.executable,
             '-c',
             "import atexit, time, sys; atexit.register(lambda : print('called atexit')); print('sleeping'); sys.stdout.flush(); time.sleep(100)"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    line = process.stdout.readline()
    assert line == b'sleeping\n'
    os.kill(process.pid, signal.SIGINT)
    process.wait()
    assert process.returncode == -signal.SIGINT
    line = process.stdout.read()
    assert line == b'called atexit\n'

