import sys, os, thread, time, signal

os.setpgid(0, 0)
assert os.getpgrp() == os.getpid()


sys.path[:] = sys.argv[1].split('\x7f')
from rpython.translator.revdb.process import ReplayProcessGroup

exename, rdbname = sys.argv[2:]
group = ReplayProcessGroup(exename, rdbname)


class MyInterrupt(Exception):
    pass
def my_signal(*args):
    raise MyInterrupt
prev_signal = signal.signal(signal.SIGINT, my_signal)

def enable_timer():
    def my_kill():
        time.sleep(0.8)
        print >> sys.stderr, "--<<< Sending CTRL-C >>>--"
        os.killpg(os.getpid(), signal.SIGINT)
    thread.start_new_thread(my_kill, ())

all_ok = False
try:
    # this runs for ~9 seconds if uninterrupted
    enable_timer()
    group.print_cmd('very-long-loop')
except MyInterrupt:
    print >> sys.stderr, "very-long-loop interrupted, trying again"
    group.recreate_subprocess(1)
    try:
        enable_timer()
        group.print_cmd('very-long-loop')
    except MyInterrupt:
        print >> sys.stderr, "second interruption ok"
        all_ok = True

assert all_ok, "expected very-long-loop to be killed by SIGINT"
print "all ok"
