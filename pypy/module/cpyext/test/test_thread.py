import py

import thread
import threading

from pypy.module.thread.ll_thread import allocate_ll_lock
from pypy.module.cpyext.test.test_api import BaseApiTest


class TestPyThread(BaseApiTest):
    def test_get_thread_ident(self, space, api):
        results = []
        def some_thread():
            res = api.PyThread_get_thread_ident()
            results.append((res, thread.get_ident()))

        some_thread()
        assert results[0][0] == results[0][1]

        th = threading.Thread(target=some_thread, args=())
        th.start()
        th.join()
        assert results[1][0] == results[1][1]

        assert results[0][0] != results[1][0]

    def test_acquire_lock(self, space, api):
        assert hasattr(api, 'PyThread_acquire_lock')
        lock = api.PyThread_allocate_lock()
        assert api.PyThread_acquire_lock(lock, 1) == 1
        assert api.PyThread_acquire_lock(lock, 0) == 0
        api.PyThread_free_lock(lock)

    def test_release_lock(self, space, api):
        assert hasattr(api, 'PyThread_acquire_lock')
        lock = api.PyThread_allocate_lock()
        api.PyThread_acquire_lock(lock, 1)
        api.PyThread_release_lock(lock)
        assert api.PyThread_acquire_lock(lock, 0) == 1
        api.PyThread_free_lock(lock)
