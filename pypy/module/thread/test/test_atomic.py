from __future__ import with_statement
from pypy.module.thread.test.support import GenericTestThread


class AppTestAtomic(GenericTestThread):

    def test_simple(self):
        import thread
        with thread.atomic:
            pass
        try:
            with thread.atomic:
                raise ValueError
        except ValueError:
            pass
