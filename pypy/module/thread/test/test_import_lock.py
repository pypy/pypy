from pypy.module.thread.test.support import GenericTestThread


class AppTestThread(GenericTestThread):

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
