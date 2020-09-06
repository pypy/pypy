import pytest
import time
from rpython.rlib.rgil import yield_thread
from pypy.tool.pytest.objspace import gettestobjspace
from pypy.interpreter.gateway import interp2app
from pypy.module.thread.os_lock import allocate_lock
from pypy.module.thread.os_thread import start_new_thread
from pypy.module._multiprocessing.interp_semaphore import (
    create_semaphore, delete_semaphore, W_SemLock)


@pytest.mark.parametrize('spaceconfig', [
    {'usemodules': ['_multiprocessing', 'thread']}])
def test_semlock_release(space):
    # trigger the setup() code in time.moduledef
    space.getbuiltinmodule('time')
    sem_name = '/test8'
    _handle = create_semaphore(space, sem_name, 1, 1)
    try:
        w_lock = W_SemLock(space, _handle, 0, 1)
        created = []
        successful = []
        N_THREADS = 16

        def run(space):
            w_sentinel = allocate_lock(space)
            yield_thread()
            w_sentinel.descr_lock_acquire(space)  # releases GIL
            try:
                yield_thread()
                created.append(w_sentinel)
                w_got = w_lock.acquire(space, w_timeout=space.newfloat(5.))  # releases GIL
                if space.is_true(w_got):
                    yield_thread()
                    w_lock.release(space)
                    successful.append(w_sentinel)
                w_sentinel.descr_lock_release(space)
            except:
                import traceback
                traceback.print_exc()
                w_sentinel.descr_lock_release(space)
                raise
        w_run = space.wrap(interp2app(run))

        w_lock.acquire(space)
        for _ in range(N_THREADS):
            start_new_thread(space, w_run, space.newtuple([]))  # releases GIL
        deadline = time.time() + 5.
        while len(created) < N_THREADS:
            assert time.time() < deadline
            yield_thread()
        w_lock.release(space)

        for w_sentinel in created:
            # Join thread
            w_sentinel.descr_lock_acquire(space)  # releases GIL
            w_sentinel.descr_lock_release(space)
        assert len(successful) == N_THREADS
    finally:
        delete_semaphore(_handle)
