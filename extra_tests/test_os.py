import os
import sys
from pytest import raises, skip

python = sys.executable

if hasattr(os, "execv"):
    def test_execv():
        if not hasattr(os, "fork"):
            skip("Need fork() to test execv()")
        if not os.path.isdir('/tmp'):
            skip("Need '/tmp' for test")
        pid = os.fork()
        if pid == 0:
            os.execv("/usr/bin/env", ["env", python, "-c",
                     ("fid = open('/tmp/onefile0', 'w'); "
                      "fid.write('1'); "
                      "fid.close()")])
        os.waitpid(pid, 0)
        assert open("/tmp/onefile0").read() == "1"
        os.unlink("/tmp/onefile0")

    def test_execv_raising():
        with raises(OSError):
            os.execv("saddsadsadsadsa", ["saddsadsasaddsa"])

    def test_execv_no_args():
        with raises(ValueError):
            os.execv("notepad", [])
        # PyPy needs at least one arg, CPython 2.7 is fine without
        with raises(ValueError):
            os.execve("notepad", [], {})

    def test_execv_raising2():
        for n in 3, [3, "a"]:
            with raises(TypeError):
                os.execv("xxx", n)

    def test_execv_unicode():
        if not hasattr(os, "fork"):
            skip("Need fork() to test execv()")
        if not os.path.isdir('/tmp'):
            skip("Need '/tmp' for test")
        try:
            output = u"caf\xe9 \u1234\n".encode(sys.getfilesystemencoding())
        except UnicodeEncodeError:
            skip("encoding not good enough")
        pid = os.fork()
        if pid == 0:
            os.execv(u"/bin/sh", ["sh", "-c",
                                  u"echo caf\xe9 \u1234 > /tmp/onefile1"])
        os.waitpid(pid, 0)
        with open("/tmp/onefile1") as fid:
            assert fid.read() == output
        os.unlink("/tmp/onefile1")

    def test_execve():
        if not hasattr(os, "fork"):
            skip("Need fork() to test execve()")
        pid = os.fork()
        if pid == 0:
            os.execve("/usr/bin/env", ["env", python, "-c",
                      ("import os; fid = open('onefile', 'w'); "
                       "fid.write(os.environ['ddd']); "
                       "fid.close()")],
                      {'ddd': 'xxx'})
        os.waitpid(pid, 0)
        assert open("onefile").read() == "xxx"
        os.unlink("onefile")

    def test_execve_unicode():
        if not hasattr(os, "fork"):
            skip("Need fork() to test execve()")
        try:
            output = u"caf\xe9 \u1234\n".encode(sys.getfilesystemencoding())
        except UnicodeEncodeError:
            skip("encoding not good enough")
        pid = os.fork()
        if pid == 0:
            os.execve(u"/bin/sh", ["sh", "-c",
                                   u"echo caf\xe9 \u1234 > onefile"],
                      {'ddd': 'xxx'})
        os.waitpid(pid, 0)
        with open("onefile") as fid:
            assert fid.read() == output
        os.unlink("onefile")
    pass  # <- please, inspect.getsource(), don't crash

if hasattr(os, "spawnv"):
    def test_spawnv():
        ret = os.spawnv(os.P_WAIT, python,
                        [python, '-c', 'raise(SystemExit(42))'])
        assert ret == 42

if hasattr(os, "spawnve"):
    def test_spawnve():
        env = {'PATH': os.environ['PATH'], 'FOOBAR': '42'}
        cmd = "raise(SystemExit(int(__import__('os').environ['FOOBAR'])))"
        ret = os.spawnve(os.P_WAIT, python, [python, '-c', cmd], env)
        assert ret == 42
