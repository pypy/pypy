import py, sys
from pypy.conftest import gettestobjspace
from pypy.module.thread.test.support import GenericTestThread

class AppTestFork(GenericTestThread):
    def test_fork(self):
        # XXX This test depends on a multicore machine, as busy_thread must
        # aquire the GIL the instant that the main thread releases it.
        # It will incorrectly pass if the GIL is not grabbed in time.
        import thread
        import os
        import time

        if not hasattr(os, 'fork'):
            skip("No fork on this platform")

        run = True
        done = []
        def busy_thread():
            while run:
                time.sleep(0)
            done.append(None)

        try:
            thread.start_new(busy_thread, ())

            pid = os.fork()

            if pid == 0:
                os._exit(0)

            else:
                time.sleep(1)
                spid, status = os.waitpid(pid, os.WNOHANG)
                assert spid == pid
        finally:
            run = False
            self.waitfor(lambda: done)
