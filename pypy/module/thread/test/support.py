import py
from pypy.conftest import gettestobjspace

class GenericTestThread:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('thread',))
        cls.space = space

        cls.w_waitfor = space.appexec([], """():
            import time
            def waitfor(expr, timeout=10.0):
                limit = time.time() + timeout
                while time.time() <= limit:
                    time.sleep(0.002)
                    if expr():
                        return
                print '*** timed out ***'
            return waitfor
        """)
        cls.w_busywait = space.appexec([], """():
            import time
            def busywait(t):
                limit = time.time() + t
                while time.time() <= limit:
                    time.sleep(0.002)
            return busywait
        """)
