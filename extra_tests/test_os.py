import os

if hasattr(__import__(os.name), "execv"):
    def test_execv(self):
        os = self.posix
        if not hasattr(os, "fork"):
            skip("Need fork() to test execv()")
        pid = os.fork()
        if pid == 0:
            os.execv("/usr/bin/env", ["env", self.python, "-c",
                     ("fid = open('onefile', 'w'); "
                      "fid.write('1'); "
                      "fid.close()")])
        os.waitpid(pid, 0)
        assert open("onefile").read() == "1"
        os.unlink("onefile")

    def test_execv_raising(self):
        os = self.posix
        with raises(OSError):
            os.execv("saddsadsadsadsa", ["saddsadsasaddsa"])

    def test_execv_no_args(self):
        os = self.posix
        with raises(ValueError):
            os.execv("notepad", [])
        with raises(ValueError):
            os.execve("notepad", [], {})

    def test_execv_raising2(self):
        os = self.posix
        for n in 3, [3, "a"]:
            with raises(TypeError) as excinfo:
                os.execv("xxx", n)

    def test_execv_unicode(self):
        os = self.posix
        import sys
        if not hasattr(os, "fork"):
            skip("Need fork() to test execv()")
        try:
            output = u"caf\xe9 \u1234\n".encode(sys.getfilesystemencoding())
        except UnicodeEncodeError:
            skip("encoding not good enough")
        pid = os.fork()
        if pid == 0:
            os.execv(u"/bin/sh", ["sh", "-c",
                                  u"echo caf\xe9 \u1234 > onefile"])
        os.waitpid(pid, 0)
        with open("onefile") as fid:
            assert fid.read() == output
        os.unlink("onefile")

    def test_execve(self):
        os = self.posix
        if not hasattr(os, "fork"):
            skip("Need fork() to test execve()")
        pid = os.fork()
        if pid == 0:
            os.execve("/usr/bin/env", ["env", self.python, "-c",
                      ("import os; fid = open('onefile', 'w'); "
                       "fid.write(os.environ['ddd']); "
                       "fid.close()")],
                      {'ddd':'xxx'})
        os.waitpid(pid, 0)
        assert open("onefile").read() == "xxx"
        os.unlink("onefile")

    def test_execve_unicode(self):
        os = self.posix
        import sys
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
    pass # <- please, inspect.getsource(), don't crash

if hasattr(__import__(os.name), "spawnv"):
    # spawnv is from stdlib's os, so this test is never run
    def test_spawnv(self):
        os = self.posix
        import sys
        ret = os.spawnv(os.P_WAIT, self.python,
                        [self.python, '-c', 'raise(SystemExit(42))'])
        assert ret == 42

if hasattr(__import__(os.name), "spawnve"):
    # spawnve is from stdlib's os, so this test is never run
    def test_spawnve(self):
        os = self.posix
        env = {'PATH':os.environ['PATH'], 'FOOBAR': '42'}
        ret = os.spawnve(os.P_WAIT, self.python,
                         [self.python, '-c',
                          "raise(SystemExit(int(__import__('os').environ['FOOBAR'])))"],
                         env)
        assert ret == 42


