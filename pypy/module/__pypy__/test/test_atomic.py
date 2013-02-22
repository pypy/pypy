from __future__ import with_statement
from pypy.module.thread.test.support import GenericTestThread
from pypy.module.__pypy__.interp_atomic import bdecode
from rpython.rtyper.lltypesystem import rffi


def test_bdecode():
    class FakeSpace:
        def wrap(self, x):
            assert isinstance(x, str)
            return x
        def int(self, x):
            assert isinstance(x, str)
            return int(x)
        def newlist(self, lst):
            assert isinstance(lst, list)
            return lst

    space = FakeSpace()

    def bdec(s):
        p = rffi.str2charp(s)
        w_obj, q = bdecode(space, p)
        assert q == rffi.ptradd(p, len(s))
        rffi.free_charp(p)
        return w_obj

    assert bdec("i123e") == 123
    assert bdec("i-123e") == -123
    assert bdec('12:+"*-%&/()=?\x00') == '+"*-%&/()=?\x00'
    assert bdec("li123eli456eee") == [123, [456]]
    assert bdec("l5:abcdei2ee") == ["abcde", 2]


class AppTestAtomic(GenericTestThread):

    def test_simple(self):
        from __pypy__ import thread
        for atomic in thread.atomic, thread.exclusive_atomic:
            with atomic:
                pass
            try:
                with atomic:
                    raise ValueError
            except ValueError:
                pass

    def test_nest_composable_atomic(self):
        from __pypy__ import thread
        with thread.atomic:
            with thread.atomic:
                pass

    def test_nest_composable_below_exclusive(self):
        from __pypy__ import thread
        with thread.exclusive_atomic:
            with thread.atomic:
                with thread.atomic:
                    pass

    def test_nest_exclusive_fails(self):
        from __pypy__ import thread
        try:
            with thread.exclusive_atomic:
                with thread.exclusive_atomic:
                    pass
        except thread.error, e:
            assert e.message == "exclusive_atomic block can't be entered inside another atomic block"

    def test_nest_exclusive_fails2(self):
        from __pypy__ import thread
        try:
            with thread.atomic:
                with thread.exclusive_atomic:
                    pass
        except thread.error, e:
            assert e.message == "exclusive_atomic block can't be entered inside another atomic block"
