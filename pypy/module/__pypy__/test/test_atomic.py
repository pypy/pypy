from __future__ import with_statement
from pypy.module.thread.test.support import GenericTestThread
from rpython.rtyper.lltypesystem import rffi


class AppTestAtomic(GenericTestThread):

    def test_simple(self):
        from __pypy__ import thread
        for atomic in thread.atomic, thread.exclusive_atomic:
            with atomic:
                assert thread.is_atomic()
            try:
                with atomic:
                    raise ValueError
            except ValueError:
                pass

    def test_nest_composable_atomic(self):
        from __pypy__ import thread
        with thread.atomic:
            with thread.atomic:
                assert thread.is_atomic()
            assert thread.is_atomic()
        assert not thread.is_atomic()

    def test_nest_composable_below_exclusive(self):
        from __pypy__ import thread
        with thread.exclusive_atomic:
            with thread.atomic:
                with thread.atomic:
                    assert thread.is_atomic()
                assert thread.is_atomic()
            assert thread.is_atomic()
        assert not thread.is_atomic()

    def test_nest_exclusive_fails(self):
        from __pypy__ import thread
        try:
            with thread.exclusive_atomic:
                with thread.exclusive_atomic:
                    assert thread.is_atomic()
        except thread.error, e:
            assert not thread.is_atomic()
            assert e.message == "exclusive_atomic block can't be entered inside another atomic block"

    def test_nest_exclusive_fails2(self):
        from __pypy__ import thread
        try:
            with thread.atomic:
                with thread.exclusive_atomic:
                    assert thread.is_atomic()
                assert thread.is_atomic()
        except thread.error, e:
            assert not thread.is_atomic()
            assert e.message == "exclusive_atomic block can't be entered inside another atomic block"
