import sys
import util
import signal

def test_busywait(monkeypatch):
    class FakeProcess:
        def poll(self):
            if timers[0] >= timers[1]:
                return 42
            return None
    class FakeTime:
        def sleep(self, delay):
            timers[0] += delay
        def time(self):
            timers[2] += 1
            return 12345678.9 + timers[0]
    p = FakeProcess()
    
    monkeypatch.setattr(util, 'time', FakeTime())
    #
    timers = [0.0, 0.0, 0]
    returncode = util.busywait(p, 10)
    assert returncode == 42 and 0.0 <= timers[0] <= 1.0
    #
    timers = [0.0, 3.0, 0]
    returncode = util.busywait(p, 10)
    assert returncode == 42 and 3.0 <= timers[0] <= 5.0 and timers[2] <= 10
    #
    timers = [0.0, 500.0, 0]
    returncode = util.busywait(p, 1000)
    assert returncode == 42 and 500.0<=timers[0]<=510.0 and timers[2]<=100
    #
    timers = [0.0, 500.0, 0]
    returncode = util.busywait(p, 100)    # get a timeout
    assert returncode == None and 100.0 <= timers[0] <= 110.0
    #

def test_should_report_failure():
    should_report_failure = util.should_report_failure
    assert should_report_failure("")
    assert should_report_failure(". Abc\n. Def\n")
    assert should_report_failure("s Ghi\n")
    assert not should_report_failure(". Abc\nF Def\n")
    assert not should_report_failure(". Abc\nE Def\n")
    assert not should_report_failure(". Abc\nP Def\n")
    assert not should_report_failure("F Def\n. Ghi\n. Jkl\n")


class TestRunHelper(object):
    def pytest_funcarg__out(self, request):
        tmpdir = request.getfuncargvalue('tmpdir')
        return tmpdir.ensure('out')

    def test_run(self, out):
        res = util.run([sys.executable, "-c", "print 42"], '.', out)
        assert res == 0
        assert out.read() == "42\n"

    def test_error(self, out):
        res = util.run([sys.executable, "-c", "import sys; sys.exit(3)"], '.', out)
        assert res == 3

    def test_signal(self, out):
        if sys.platform == 'win32':
            py.test.skip("no death by signal on windows")
        res = util.run([sys.executable, "-c", "import os; os.kill(os.getpid(), 9)"], '.', out)
        assert res == -9

    def test_timeout(self, out):
        res = util.run([sys.executable, "-c", "while True: pass"], '.', out, timeout=3)
        assert res == -999

    def test_timeout_lock(self, out):
        res = util.run([sys.executable, "-c", "import threading; l=threading.Lock(); l.acquire(); l.acquire()"], '.', out, timeout=3)
        assert res == -999

    def test_timeout_syscall(self, out):
        res = util.run([sys.executable, "-c", "import socket; s=s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(('', 0)); s.recv(1000)"], '.', out, timeout=3)
        assert res == -999        

    def test_timeout_success(self, out):
        res = util.run([sys.executable, "-c", "print 42"], '.',
                         out, timeout=2)
        assert res == 0
        out = out.read()
        assert out == "42\n"        



def test_interpret_exitcode():
    failure, extralog = util.interpret_exitcode(0, "test_foo")
    assert not failure
    assert extralog == ""

    failure, extralog = util.interpret_exitcode(1, "test_foo", "")
    assert failure
    assert extralog == """! test_foo
 Exit code 1.
"""

    failure, extralog = util.interpret_exitcode(1, "test_foo", "F Foo\n")
    assert failure
    assert extralog == ""

    failure, extralog = util.interpret_exitcode(2, "test_foo")
    assert failure
    assert extralog == """! test_foo
 Exit code 2.
"""
    failure, extralog = util.interpret_exitcode(-signal.SIGSEGV,
                                                  "test_foo")
    assert failure
    assert extralog == """! test_foo
 Killed by SIGSEGV.
"""
