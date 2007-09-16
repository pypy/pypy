from pypy.tool.udir import udir
from pypy.module.thread.test.support import GenericTestThread


class AppTestThread(GenericTestThread):

    def setup_class(cls):
        GenericTestThread.setup_class.im_func(cls)
        tmpdir = str(udir.ensure('test_import_lock', dir=1))
        cls.w_tmpdir = cls.space.wrap(tmpdir)

    def test_import_lock(self):
        import thread, imp
        assert not imp.lock_held()
        done = []
        def f():
            print '[ENTER %d]' % i
            from imghdr import testall
            print '[LEAVE %d]' % i
            done.append(1)
        for i in range(5):
            print '[RUN %d]' % i
            thread.start_new_thread(f, ())
        self.waitfor(lambda: len(done) == 5)
        assert len(done) == 5

    def test_with_many_dependencies(self):
        import thread
        import re      # -> causes nested imports

    def test_manual_locking(self):
        import thread, os, imp, time, sys
        f = open(os.path.join(self.tmpdir, 'foobaz2.py'), 'w')
        f.close()   # empty
        done = []
        def f():
            sys.path.insert(0, self.tmpdir)
            import foobaz2
            p = sys.path.pop(0)
            assert p == self.tmpdir
            done.append(1)
        assert not imp.lock_held()
        imp.acquire_lock()
        assert imp.lock_held()
        thread.start_new_thread(f, ())
        time.sleep(0.9)
        assert not done
        assert imp.lock_held()
        # check that it's a recursive lock
        imp.acquire_lock()
        assert imp.lock_held()
        imp.acquire_lock()
        assert imp.lock_held()
        imp.release_lock()
        assert imp.lock_held()
        imp.release_lock()
        assert imp.lock_held()
        imp.release_lock()
        assert not imp.lock_held()
        self.waitfor(lambda: done)
        assert done
