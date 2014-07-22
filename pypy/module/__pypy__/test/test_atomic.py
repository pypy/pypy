from __future__ import with_statement
from pypy.module.thread.test.support import GenericTestThread
from rpython.rtyper.lltypesystem import rffi


def test_bdecode(space):
    from pypy.module.__pypy__.interp_atomic import bdecode
    def bdec(s, expected):
        p = rffi.str2charp(s)
        w_obj, q = bdecode(space, p)
        assert q == rffi.ptradd(p, len(s))
        rffi.free_charp(p)
        w_expected = space.wrap(expected)
        assert space.eq_w(w_obj, w_expected)

    bdec("i123e", 123)
    bdec("i-123e", -123)
    bdec('12:+"*-%&/()=?\x00', '+"*-%&/()=?\x00')
    bdec("li123eli456eee", [123, [456]])
    bdec("l5:abcdei2ee", ["abcde", 2])


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
