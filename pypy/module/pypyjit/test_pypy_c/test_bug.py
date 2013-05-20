import os, sys, py, subprocess

localdir = os.path.dirname(os.path.abspath(__file__))


def test_bug1():
    if not sys.platform.startswith('linux'):
        py.test.skip("linux-only test")

    cmdline = ['taskset', '-c', '0',
               sys.executable, os.path.join(localdir, 'bug1.py')]
    popen = subprocess.Popen(cmdline)
    err = popen.wait()
    assert err == 0
