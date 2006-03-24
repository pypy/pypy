import py
import time, gc
from pypy.conftest import gettestobjspace
from pypy.interpreter.gateway import ObjSpace, W_Root, interp2app_temp


def waitfor(space, w_condition, timeout=300.0):
    w_sleep = space.appexec([], "():\n import time; return time.sleep")
    adaptivedelay = 0.04
    limit = time.time() + timeout
    while time.time() <= limit:
        space.call_function(w_sleep, space.wrap(adaptivedelay))
        gc.collect()
        if space.is_true(space.call_function(w_condition)):
            return
        adaptivedelay *= 1.05
    print '*** timed out ***'
waitfor.unwrap_spec = [ObjSpace, W_Root, float]


class GenericTestThread:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('thread', 'time'))
        cls.space = space

        cls.w_waitfor = space.wrap(interp2app_temp(waitfor))
        cls.w_busywait = space.appexec([], """():
            import time
            return time.sleep
        """)

##        cls.w_waitfor = space.appexec([], """():
##            import time
##            def waitfor(expr, timeout=10.0):
##                limit = time.time() + timeout
##                while time.time() <= limit:
##                    time.sleep(0.002)
##                    if expr():
##                        return
##                print '*** timed out ***'
##            return waitfor
##        """)
##        cls.w_busywait = space.appexec([], """():
##            import time
##            def busywait(t):
##                limit = time.time() + t
##                while time.time() <= limit:
##                    time.sleep(0.002)
##            return busywait
##        """)

##        space.appexec([], """():
##            import sys
##            sys.setcheckinterval(1)
##        """)
