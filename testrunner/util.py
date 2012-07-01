import sys
import os
import subprocess
import signal
import time
import optparse

parser = optparse.OptionParser()
parser.add_option("--logfile", dest="logfile", default=None,
                  help="accumulated machine-readable logfile")
parser.add_option("--output", dest="output", default='-',
                  help="plain test output (default: stdout)")
parser.add_option("--config", dest="config", default=[],
                  action="append",
                  help="configuration python file (optional)")
parser.add_option("--root", dest="root", default=".",
                  help="root directory for the run")
parser.add_option("--parallel-runs", dest="parallel_runs", default=0,
                  type="int",
                  help="number of parallel test runs")
parser.add_option("--dry-run", dest="dry_run", default=False,
                  action="store_true",
                  help="dry run"),
parser.add_option("--timeout", dest="timeout", default=None,
                  type="int",
                  help="timeout in secs for test processes")




if sys.platform == 'win32':
    PROCESS_TERMINATE = 0x1
    try:
        import win32api, pywintypes
    except ImportError:
        def _kill(pid, sig):
            import ctypes
            winapi = ctypes.windll.kernel32
            proch = winapi.OpenProcess(PROCESS_TERMINATE, 0, pid)
            winapi.TerminateProcess(proch, 1) == 1
            winapi.CloseHandle(proch)
    else:
        def _kill(pid, sig):
            try:
                proch = win32api.OpenProcess(PROCESS_TERMINATE, 0, pid)
                win32api.TerminateProcess(proch, 1)
                win32api.CloseHandle(proch)
            except pywintypes.error:
                pass
    #Try to avoid opeing a dialog box if one of the tests causes a system error
    import ctypes
    winapi = ctypes.windll.kernel32
    SetErrorMode = winapi.SetErrorMode
    SetErrorMode.argtypes=[ctypes.c_int]

    SEM_FAILCRITICALERRORS = 1
    SEM_NOGPFAULTERRORBOX  = 2
    SEM_NOOPENFILEERRORBOX = 0x8000
    flags = SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX
    #Since there is no GetErrorMode, do a double Set
    old_mode = SetErrorMode(flags)
    SetErrorMode(old_mode | flags)

    SIGKILL = SIGTERM = 0
else:
    def _kill(pid, sig):
        try:
            os.kill(pid, sig)
        except OSError:
            pass

    SIGKILL = signal.SIGKILL
    SIGTERM = signal.SIGTERM


EXECUTEFAILED = -1001
RUNFAILED  = -1000
TIMEDOUT = -999


def getsignalname(n):
    for name, value in signal.__dict__.items():
        if value == n and name.startswith('SIG'):
            return name
    return 'signal %d' % (n,)


def should_report_failure(logdata):
    # When we have an exitcode of 1, it might be because of failures
    # that occurred "regularly", or because of another crash of py.test.
    # We decide heuristically based on logdata: if it looks like it
    # contains "F", "E" or "P" then it's a regular failure, otherwise
    # we have to report it.
    for line in logdata.splitlines():
        if (line.startswith('F ') or
            line.startswith('E ') or
            line.startswith('P ')):
            return False
    return True



def busywait(p, timeout):
    t0 = time.time()
    delay = 0.5
    while True:
        time.sleep(delay)
        returncode = p.poll()
        if returncode is not None:
            return returncode
        tnow = time.time()
        if (tnow-t0) >= timeout:
            return None
        delay = min(delay * 1.15, 7.2)



def interpret_exitcode(exitcode, test, logdata=""):
    extralog = ""
    if exitcode:
        failure = True
        if exitcode != 1 or should_report_failure(logdata):
            if exitcode > 0:
                msg = "Exit code %d." % exitcode
            elif exitcode == TIMEDOUT:
                msg = "TIMEOUT"
            elif exitcode == RUNFAILED:
                msg = "Failed to run interp"
            elif exitcode == EXECUTEFAILED:
                msg = "Failed with exception in execute-test"
            else:
                msg = "Killed by %s." % getsignalname(-exitcode)
            extralog = "! %s\n %s\n" % (test, msg)
    else:
        failure = False
    return failure, extralog



def run(args, cwd, out, timeout=None):
    with out.open('w') as f:
        try:
            p = subprocess.Popen(args, cwd=str(cwd), stdout=f, stderr=f)
        except Exception, e:
            f.write("Failed to run %s with cwd='%s' timeout=%s:\n"
                    " %s\n"
                    % (args, cwd, timeout, e))
            return RUNFAILED

        if timeout is None:
            return p.wait()
        else:
            returncode = busywait(p, timeout)
            if returncode is not None:
                return returncode
            # timeout!
            _kill(p.pid, SIGTERM)
            if busywait(p, 10) is None:
                _kill(p.pid, SIGKILL)
            return TIMEDOUT


def dry_run(args, cwd, out, timeout=None):
    with out.open('w') as f:
        f.write("run %s with cwd='%s' timeout=%s\n" % (args, cwd, timeout))
    return 0
