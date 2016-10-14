import py
import sys

from pypy.module._multiprocessing.interp_semaphore import (
    RECURSIVE_MUTEX, SEMAPHORE)


class AppTestSemaphore:
    spaceconfig = dict(usemodules=('_multiprocessing', 'thread',
                                   'signal', 'select',
                                   'binascii', 'struct', '_posixsubprocess'))

    if sys.platform == 'win32':
        spaceconfig['usemodules'] += ('_rawffi',)
    else:
        spaceconfig['usemodules'] += ('fcntl',)

    def setup_class(cls):
        cls.w_SEMAPHORE = cls.space.wrap(SEMAPHORE)
        cls.w_RECURSIVE = cls.space.wrap(RECURSIVE_MUTEX)

    @py.test.mark.skipif("sys.platform == 'win32'")
    def test_sem_unlink(self):
        from _multiprocessing import sem_unlink
        try: sem_unlink("non-existent")
        except OSError: pass

    def test_semaphore(self):
        from _multiprocessing import SemLock
        import sys
        assert SemLock.SEM_VALUE_MAX > 10

        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        # the following line gets OSError: [Errno 38] Function not implemented
        # if /dev/shm is not mounted on Linux
        sem = SemLock(kind, value, maxvalue, "1", False)
        assert sem.kind == kind
        assert sem.maxvalue == maxvalue
        assert isinstance(sem.handle, int)

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

        sem.acquire()
        sem._after_fork()
        assert sem._count() == 0

    def test_recursive(self):
        from _multiprocessing import SemLock
        kind = self.RECURSIVE
        value = 1
        maxvalue = 1
        # the following line gets OSError: [Errno 38] Function not implemented
        # if /dev/shm is not mounted on Linux
        sem = SemLock(kind, value, maxvalue, "2", False)

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
        sem = SemLock(kind, value, maxvalue, "3", False)

        res = sem.acquire()
        assert res == True
        res = sem.acquire(timeout=0.1)
        assert res == False

    def test_semaphore_rebuild(self):
        from _multiprocessing import SemLock
        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue, "4", False)

        sem2 = SemLock._rebuild(sem.handle, kind, value, "10")
        assert sem.handle == sem2.handle

    def test_semaphore_contextmanager(self):
        from _multiprocessing import SemLock
        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue, "5", False)

        with sem:
            assert sem._count() == 1
        assert sem._count() == 0
