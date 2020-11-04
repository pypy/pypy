import py
import sys, os, subprocess


CODE = """
import sys, os, thread, time

fd1, fd2 = os.pipe()
f1 = os.fdopen(fd1, 'r', 0)
f2 = os.fdopen(fd2, 'w', 0)

def f():
    print "thread started"
    x = f1.read(1)
    assert x == "X"
    print "thread exit"

thread.start_new_thread(f, ())
time.sleep(0.5)
if os.fork() == 0:   # in the child
    time.sleep(0.5)
    x = f1.read(1)
    assert x == "Y"
    print "ok!"
    sys.exit()

f2.write("X")   # in the parent
f2.write("Y")   # in the parent
time.sleep(1.0)
"""


def test_thread_fork_file_lock():
    if not hasattr(os, 'fork'):
        py.test.skip("requires 'fork'")
    output = subprocess.check_output([sys.executable, '-u', '-c', CODE])
    assert output.splitlines() == [
        'thread started',
        'thread exit',
        'ok!']
