from pypy.tool.udir import udir
from pypy.module.thread.test.support import GenericTestThread


class AppTestThread(GenericTestThread):

    def setup_class(cls):
        GenericTestThread.setup_class.im_func(cls)
        tmpdir = str(udir.ensure('test_import_lock', dir=1))
        cls.w_tmpdir = cls.space.wrap(tmpdir)

    def test_import_lock(self):
        import thread
        done = []
        def f():
            from imghdr import testall
            done.append(1)
        for i in range(5):
            thread.start_new_thread(f, ())
        self.waitfor(lambda: len(done) == 5)
        assert len(done) == 5

    def test_with_many_dependencies(self):
        import thread
        import re      # -> causes nested imports

    def test_no_lock_for_reimporting(self):
        # CPython deadlocks in this situation; in our case the property
        # of not requiring the import lock for already-imported modules
        # is useful for translation, to avoid needing a prebuilt import
        # lock object.
        import os, sys
        f = open(os.path.join(self.tmpdir, 'foobaz1.py'), 'w')
        print >> f, """if 1:
            import thread
            lock = thread.allocate_lock()
            lock.acquire()
            def f():
                import sys
                lock.release()
            thread.start_new_thread(f, ())
            lock.acquire()
        """
        f.close()
        sys.path.insert(0, self.tmpdir)
        import foobaz1
