from _multiprocessing import SemLock
from threading import Thread
import time


def test_notify_all():
    """A low-level variation on test_notify_all() in lib-python's
    _test_multiprocessing.py
    """
    N_THREADS = 1000
    lock = SemLock(0, 1, 1, "/test_notify_all", True)
    results = []

    def f(n):
        if lock.acquire(timeout=5.):
            results.append(n)
            lock.release()

    threads = [Thread(target=f, args=(i,)) for i in range(N_THREADS)]
    with lock:
        for t in threads:
            t.start()
        time.sleep(0.1)
    for t in threads:
        t.join()
    assert len(results) == N_THREADS
