
""" In this file we define all necessary stuff
build around subprocess to run python console in it
"""

KILL_TIMEOUT = 300
TIMEOUT = 10

""" The idea behind is that we create xmlhttprequest immediataly
and reply with new data (if available) or reply anyway
after TIMEOUT
"""

import py
import subprocess
from Queue import Queue
from py.__.green.greensock2 import autogreenlet, Timer, Interrupted,\
     meetingpoint
from py.__.green.pipe.fd import FDInput
from py.magic import greenlet
import time

class Killed(Exception):
    pass

class Interpreter(object):
    def __init__(self, python, timeout=TIMEOUT, kill_timeout=KILL_TIMEOUT):
        pipe = subprocess.Popen([python, "-u", "-i"], stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                            close_fds=True, bufsize=0)
        self.pipe = pipe
        self.read_fd = FDInput(self.pipe.stdout.fileno(), close=False)
        self.pid = pipe.pid
        self.timeout = timeout
        #self.kill_timeout = kill_timeout
        self.giver, accepter = meetingpoint()
        autogreenlet(self.timeout_kill, accepter, kill_timeout)
        #self.last_activity = time.time()

    def timeout_kill(self, accepter, timeout):
        while 1:
            try:
                self.kill_timer = Timer(timeout)
                accepter.accept()
                self.kill_timer.stop()
            except Interrupted:
                self.close()
                return

    def timeout_read(self, fd, timeout):
        timer = Timer(timeout)
        try:
            data = fd.recv(10024)
        except Interrupted:
            data = None
        else:
            timer.stop()
        return data

    def write_only(self, to_write):
        if to_write is not None:
            self.giver.give(42)
            self.pipe.stdin.write(to_write)

    def interact(self, to_write=None):
        self.write_only(to_write)
        return self.timeout_read(self.read_fd, self.timeout)

    def close(self):
        self.pipe.stdin.close()
        # XXX: some sane way of doing wait here? (note that wait
        #      is blocking, which means it eats all our clean interface)
        self.pipe.wait()

    __del__ = close

class InterpreterManager(object):
    pass

#class Sessions(object):
#    def __init__(self):
#        self.sessions = {}

#    def new_session(self, python="python"):
#        pipe = run_console(python)
#        self.sessions[pipe.pid] = pipe
#        return pipe.pid

#    def update_session(self, pid, to_write=None):
#        pipe = self.sessions[pid]
#        return interact(pipe, to_write)


#def interact(pipe, to_write=None):
#    if to_write is not None:
#        pipe.stdin.write(to_write + "\n")
#    try:
#        return pipe.stdout.read()
#    except IOError:
#        time.sleep(.1)
#        return ""
