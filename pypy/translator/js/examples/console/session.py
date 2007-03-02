
""" In this file we define all necessary stuff
build around subprocess to run python console in it
"""

TIMEOUT = 10

""" The idea behind is that we create xmlhttprequest immediataly
and reply with new data (if available) or reply anyway
after TIMEOUT
"""

import py
import subprocess
from Queue import Queue
from pypeers.greensock2 import autogreenlet, sleep, wait, meetingpoint
from pypeers.pipe.fd import FDInput

def timeout_read(fd, timeout):
    read = []
    giver, accepter = meetingpoint()
    
    def timeout_fun():
        sleep(timeout)
        giver.give(None)
        g_read.interrupt()

    def read_fun():
        giver.give(fd.recv(1024))
        g_timer.interrupt()

    g_timer = autogreenlet(timeout_fun)
    g_read = autogreenlet(read_fun)
    return accepter.accept()
    
class Interpreter(object):
    def __init__(self, python, timeout=TIMEOUT):
        pipe = subprocess.Popen([python, "-u", "-i"], stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                            close_fds=True, bufsize=0)
        self.pipe = pipe
        self.read_fd = FDInput(self.pipe.stdout.fileno())
        self.pid = pipe.pid
        self.timeout = timeout

    def interact(self, to_write=None):
        if to_write is not None:
            self.pipe.stdin.write(to_write)
        return timeout_read(self.read_fd, self.timeout)

    def close(self):
        self.pipe.stdin.close()
        # XXX: some sane way of doing wait here? (note that wait
        #      is blocking, which means it eats all our clean interface)
        #self.pipe.wait()

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
