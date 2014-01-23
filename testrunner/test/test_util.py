import py
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

    def pytest_funcarg__outf(self, request):
        out = request.getfuncargvalue('out')
        return out.open('w')

    def test_run(self, out, outf):
        res = util.run([sys.executable, "-c", "print 42"], '.', outf)
        assert res == 0
        assert out.read() == "42\n"

    def test_error(self, outf):
        res = util.run(
            [sys.executable, "-c", "import sys; sys.exit(3)"],
            '.', outf)
        assert res == 3

    def test_signal(self, outf):
        if sys.platform == 'win32':
            py.test.skip("no death by signal on windows")
        res = util.run(
            [sys.executable, "-c", "import os; os.kill(os.getpid(), 9)"],
            '.', outf)
        assert res == -9

    def test_timeout(self, outf):
        res = util.run(
            [sys.executable, "-c", "while True: pass"],
            '.', outf, timeout=3)
        assert res == -999

    def test_timeout_lock(self, outf):
        res = util.run(
            [sys.executable, "-c",
             "import threading; l=threading.Lock(); l.acquire(); l.acquire()"],
            '.', outf, timeout=3)
        assert res == -999

    def test_timeout_syscall(self, outf):
        res = util.run(
            [sys.executable, "-c",
             "import socket;"
             "s= socket.socket(socket.AF_INET, socket.SOCK_DGRAM);"
             "s.bind(('', 0)); s.recv(1000)"],
            '.', outf, timeout=3)
        assert res == -999

    def test_timeout_success(self, out, outf):
        res = util.run(
            [sys.executable, "-c", "print 42"], '.',
            outf, timeout=2)
        assert res == 0
        out = out.read()
        assert out == "42\n"

def make_test(id, input, expected):

    def test_interpret_exitcode():
        print(input)
        print(expected)
        failure, extralog = util.interpret_exitcode(
            input[0], 'test_foo', input[1])
        assert (failure, extralog) == expected
    test_interpret_exitcode.__name__ += str(id)
    globals()[test_interpret_exitcode.__name__] = test_interpret_exitcode

cases = [
    # input          expected output
    # exit, logdata, failure, extralog
    (0, '', False, ''),
    (1, '', True, "! test_foo\n Exit code 1.\n"),
    (1, 'F foo\n', True, '  (somefailed=True in test_foo)\n'),
    (2, '', True, "! test_foo\n Exit code 2.\n"),
    (-signal.SIGSEGV, '', True, "! test_foo\n Killed by SIGSEGV.\n"),

]

for n, i in enumerate(cases):
    make_test(n, i[:2], i[2:])

