import sys

from pypy.module._multiprocessing.interp_semaphore import (
    RECURSIVE_MUTEX, SEMAPHORE)


class AppTestSemaphore:
    spaceconfig = dict(usemodules=('_multiprocessing', 'thread',
                                   'signal', 'select',
                                   'binascii', 'struct'))

    if sys.platform == 'win32':
        spaceconfig['usemodules'] += ('_rawffi', '_cffi_backend')
    else:
        spaceconfig['usemodules'] += ('fcntl',)

    def setup_class(cls):
        cls.w_SEMAPHORE = cls.space.wrap(SEMAPHORE)
        cls.w_RECURSIVE = cls.space.wrap(RECURSIVE_MUTEX)
        cls.w_runappdirect = cls.space.wrap(cls.runappdirect)
        # import here since importing _multiprocessing imports multiprocessing
        # (in interp_connection) to get the BufferTooShort exception, which on
        # win32 imports msvcrt which imports via cffi which allocates ccharp
        # that are never released. This trips up the LeakChecker if done in a
        # test function
        cls.w_multiprocessing = cls.space.appexec([],
                                  '(): import multiprocessing as m; return m')

    def test_semaphore_basic(self):
        from _multiprocessing import SemLock
        import sys
        assert SemLock.SEM_VALUE_MAX > 10

        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        # the following line gets OSError: [Errno 38] Function not implemented
        # if /dev/shm is not mounted on Linux
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

    def test_semaphore_maxvalue(self):
        from _multiprocessing import SemLock
        import sys
        kind = self.SEMAPHORE
        value = SemLock.SEM_VALUE_MAX
        maxvalue = SemLock.SEM_VALUE_MAX
        sem = SemLock(kind, value, maxvalue)

        for i in range(10):
            res = sem.acquire()
            assert res == True
            assert sem._count() == i+1
            if sys.platform != 'darwin':
                assert sem._get_value() == maxvalue - (i+1)

        value = 0
        maxvalue = SemLock.SEM_VALUE_MAX
        sem = SemLock(kind, value, maxvalue)

        for i in range(10):
            sem.release()
            assert sem._count() == -(i+1)
            if sys.platform != 'darwin':
                assert sem._get_value() == i+1

    def test_semaphore_wait(self):
        from _multiprocessing import SemLock
        kind = self.SEMAPHORE
        value = 1
        maxvalue = 1
        sem = SemLock(kind, value, maxvalue)

        res = sem.acquire()
        assert res == True
        res = sem.acquire(timeout=0.1)
        assert res == False

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

    def test_in_threads(self):
        from _multiprocessing import SemLock
        from threading import Thread
        from time import sleep
        l = SemLock(0, 1, 1)
        if self.runappdirect:
            def f(id):
                for i in range(10000):
                    pass
        else:
            def f(id):
                for i in range(1000):
                    # reduce the probability of thread switching
                    # at exactly the wrong time in semlock_acquire
                    for j in range(10):
                        pass
        threads = [Thread(None, f, args=(i,)) for i in range(2)]
        [t.start() for t in threads]
        # if the RLock calls to sem_wait and sem_post do not match,
        # one of the threads will block and the call to join will fail
        [t.join() for t in threads]
