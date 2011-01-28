from pypy.conftest import gettestobjspace
from pypy.module._multiprocessing.interp_semaphore import (
    RECURSIVE_MUTEX, SEMAPHORE)

class AppTestSemaphore:
    def setup_class(cls):
        space = gettestobjspace(usemodules=('_multiprocessing', 'thread'))
        cls.space = space
        cls.w_SEMAPHORE = space.wrap(SEMAPHORE)
        cls.w_RECURSIVE = space.wrap(RECURSIVE_MUTEX)

    def test_semaphore(self):
        from _multiprocessing import SemLock
        import sys
        assert SemLock.SEM_VALUE_MAX > 10

        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue)
        assert sem.kind == kind
        assert sem.maxvalue == maxvalue
        assert isinstance(sem.handle, (int, long))

        assert sem._count() == 0
        if sys.platform == 'darwin':
            raises(NotImplementedError, 'sem._get_value()')
        else:
            assert sem._get_value() == 1
        assert sem._is_zero() == False
        sem.acquire()
        assert sem._is_mine()
        assert sem._count() == 1
        if sys.platform == 'darwin':
            raises(NotImplementedError, 'sem._get_value()')
        else:
            assert sem._get_value() == 0
        assert sem._is_zero() == True
        sem.release()
        assert sem._count() == 0

    def test_recursive(self):
        from _multiprocessing import SemLock
        kind = self.RECURSIVE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue)

        sem.acquire()
        sem.release()
        assert sem._count() == 0
        sem.acquire()
        sem.release()

        # now recursively
        sem.acquire()
        sem.acquire()
        assert sem._count() == 2
        sem.release()
        sem.release()

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

    def test_semaphore_contextmanager(self):
        from _multiprocessing import SemLock
        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue)

        with sem:
            assert sem._count() == 1
        assert sem._count() == 0
