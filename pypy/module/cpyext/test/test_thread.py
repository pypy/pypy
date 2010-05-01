import py

import thread
import threading

from pypy.module.thread.ll_thread import allocate_ll_lock
from pypy.module.cpyext.test.test_api import BaseApiTest


class TestPyThread(BaseApiTest):
    def test_get_thread_ident(self, space, api):
        results = []
        def some_thread():
            res = api.PyThread_get_thread_ident(space)
            results.append((res, thread.get_ident()))

        some_thread()
        assert results[0][0] == results[0][1]

        th = threading.Thread(target=some_thread, args=())
        th.start()
        th.join()
        assert results[1][0] == results[1][1]

        assert results[0][0] != results[1][0]

    @py.test.mark.xfail
    def test_acquire_lock(self, space, api):
        assert hasattr(api, 'PyThread_acquire_lock')
        lock = allocate_ll_lock()
        assert api.PyThread_acquire_lock(lock, space.w_int(0)) == 1
        assert api.PyThread_acquire_lock(lock, space.w_int(1)) == 0

    @py.test.mark.xfail
    def test_release_lock(self, space, api):
        assert hasattr(api, 'PyThread_acquire_lock')
        lock = allocate_ll_lock()
        api.PyThread_acquire_lock(lock, space.w_int(0))
        api.PyThread_release_lock(lock)
        assert api.PyThread_acquire_lock(lock, space.w_int(0)) == 1
