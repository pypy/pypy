from pypy.conftest import gettestobjspace
from pypy.module._multiprocessing.interp_semaphore import (
    RECURSIVE_MUTEX, SEMAPHORE)

class AppTestSemaphore:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
        cls.space = space
        cls.w_SEMAPHORE = space.wrap(SEMAPHORE)

    def test_semaphore(self):
        from _multiprocessing import SemLock
        assert SemLock.SEM_VALUE_MAX > 10

        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue)
        assert sem.kind == kind
        assert sem.maxvalue == maxvalue
        assert isinstance(sem.handle, int)

        assert sem._count() == 0
        sem.acquire()
        assert sem._is_mine()
        assert sem._count() == 1
        sem.release()
        assert sem._count() == 0

    def test_semaphore_wait(self):
        from _multiprocessing import SemLock
        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue)

        assert sem.acquire()
        assert not sem.acquire(timeout=0.1)

    def test_semaphore_rebuild(self):
        from _multiprocessing import SemLock
        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue)

        sem2 = SemLock._rebuild(sem.handle, kind, value)
        assert sem.handle == sem2.handle
