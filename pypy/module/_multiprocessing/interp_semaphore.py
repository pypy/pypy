from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import wrap_oserror, OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import r_uint
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.tool import rffi_platform as platform
from pypy.module.thread import ll_thread
from pypy.module._multiprocessing.interp_connection import w_handle
import sys, os, time, errno

RECURSIVE_MUTEX, SEMAPHORE = range(2)

if sys.platform == 'win32':
    from pypy.rlib import rwin32
    from pypy.interpreter.error import wrap_windowserror
    from pypy.module._multiprocessing.interp_win32 import handle_w

    SEM_VALUE_MAX = sys.maxint

    _CreateSemaphore = rwin32.winexternal(
        'CreateSemaphoreA', [rffi.VOIDP, rffi.LONG, rffi.LONG, rwin32.LPCSTR],
        rwin32.HANDLE)
    _ReleaseSemaphore = rwin32.winexternal(
        'ReleaseSemaphore', [rwin32.HANDLE, rffi.LONG, rffi.LONGP],
        rwin32.BOOL)
    _GetTickCount = rwin32.winexternal(
        'GetTickCount', [], rwin32.DWORD)

    CtrlHandler_type = lltype.Ptr(lltype.FuncType([], rwin32.BOOL))
    _CreateEvent = rwin32.winexternal(
        'CreateEventA', [rffi.VOIDP, rwin32.BOOL, rwin32.BOOL, rwin32.LPCSTR],
        rwin32.HANDLE)
    _SetEvent = rwin32.winexternal(
        'SetEvent', [rwin32.HANDLE], rwin32.BOOL)
    _ResetEvent = rwin32.winexternal(
        'ResetEvent', [rwin32.HANDLE], rwin32.BOOL)

    # This is needed because the handler function must have the "WINAPI"
    # calling convention, which is not supported by lltype.Ptr.
    eci = ExternalCompilationInfo(
        separate_module_sources=['''
            #include <windows.h>

            static BOOL (*CtrlHandlerRoutine)(
                DWORD dwCtrlType);

            static BOOL WINAPI winapi_CtrlHandlerRoutine(
              DWORD dwCtrlType)
            {
                return CtrlHandlerRoutine(dwCtrlType);
            }

            BOOL pypy_multiprocessing_setCtrlHandlerRoutine(BOOL (*f)(DWORD))
            {
                CtrlHandlerRoutine = f;
                SetConsoleCtrlHandler(winapi_CtrlHandlerRoutine, TRUE);
            }

        '''],
        export_symbols=['pypy_multiprocessing_setCtrlHandlerRoutine'],
        )
    _setCtrlHandlerRoutine = rffi.llexternal(
        'pypy_multiprocessing_setCtrlHandlerRoutine',
        [CtrlHandler_type], rwin32.BOOL,
        compilation_info=eci)

    def ProcessingCtrlHandler():
        _SetEvent(globalState.sigint_event)
        return False

    class GlobalState:
        def __init__(self):
            self.init()

        def init(self):
            self.sigint_event = rwin32.NULL_HANDLE

        def startup(self, space):
            # Initialize the event handle used to signal Ctrl-C
            globalState.sigint_event = _CreateEvent(
                rffi.NULL, True, False, rffi.NULL)
            if globalState.sigint_event == rwin32.NULL_HANDLE:
                raise wrap_windowserror(
                    space, rwin32.lastWindowsError("CreateEvent"))
            if not _setCtrlHandlerRoutine(ProcessingCtrlHandler):
                raise wrap_windowserror(
                    space, rwin32.lastWindowsError("SetConsoleCtrlHandler"))


else:
    from pypy.rlib import rposix

    eci = ExternalCompilationInfo(
        includes = ['sys/time.h',
                    'limits.h',
                    'semaphore.h'],
        libraries = ['rt'],
        )

    class CConfig:
        _compilation_info_ = eci
        TIMEVAL = platform.Struct('struct timeval', [('tv_sec', rffi.LONG),
                                                     ('tv_usec', rffi.LONG)])
        TIMESPEC = platform.Struct('struct timespec', [('tv_sec', rffi.TIME_T),
                                                       ('tv_nsec', rffi.LONG)])
        SEM_FAILED = platform.ConstantInteger('SEM_FAILED')
        SEM_VALUE_MAX = platform.ConstantInteger('SEM_VALUE_MAX')

    config = platform.configure(CConfig)
    TIMEVAL       = config['TIMEVAL']
    TIMESPEC      = config['TIMESPEC']
    TIMEVALP      = rffi.CArrayPtr(TIMEVAL)
    TIMESPECP     = rffi.CArrayPtr(TIMESPEC)
    SEM_T         = rffi.COpaquePtr('sem_t', compilation_info=eci)
    SEM_FAILED    = rffi.cast(SEM_T, config['SEM_FAILED'])
    SEM_VALUE_MAX = config['SEM_VALUE_MAX']
    HAVE_BROKEN_SEM_GETVALUE = False

    def external(name, args, result):
        return rffi.llexternal(name, args, result,
                               compilation_info=eci)

    _sem_open = external('sem_open',
                         [rffi.CCHARP, rffi.INT, rffi.INT, rffi.UINT],
                         SEM_T)
    _sem_unlink = external('sem_unlink', [rffi.CCHARP], rffi.INT)
    _sem_wait = external('sem_wait', [SEM_T], rffi.INT)
    _sem_trywait = external('sem_trywait', [SEM_T], rffi.INT)
    _sem_timedwait = external('sem_timedwait', [SEM_T, TIMESPECP], rffi.INT)
    _sem_post = external('sem_post', [SEM_T], rffi.INT)
    _sem_getvalue = external('sem_getvalue', [SEM_T, rffi.INTP], rffi.INT)

    _gettimeofday = external('gettimeofday', [TIMEVALP, rffi.VOIDP], rffi.INT)

    def sem_open(name, oflag, mode, value):
        res = _sem_open(name, oflag, mode, value)
        if res == SEM_FAILED:
            raise OSError(rposix.get_errno(), "sem_open failed")
        return res

    def sem_unlink(name):
        res = _sem_unlink(name)
        if res < 0:
            raise OSError(rposix.get_errno(), "sem_unlink failed")

    def sem_wait(sem):
        res = _sem_wait(sem)
        if res < 0:
            raise OSError(rposix.get_errno(), "sem_wait failed")

    def sem_trywait(sem):
        res = _sem_trywait(sem)
        if res < 0:
            raise OSError(rposix.get_errno(), "sem_trywait failed")

    def sem_timedwait(sem, deadline):
        res = _sem_timedwait(sem, deadline)
        if res < 0:
            raise OSError(rposix.get_errno(), "sem_timedwait failed")

    def sem_post(sem):
        res = _sem_post(sem)
        if res < 0:
            raise OSError(rposix.get_errno(), "sem_post failed")

    def sem_getvalue(sem):
        sval_ptr = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
        try:
            res = _sem_getvalue(sem, sval_ptr)
            if res < 0:
                raise OSError(rposix.get_errno(), "sem_getvalue failed")
            return rffi.cast(lltype.Signed, sval_ptr[0])
        finally:
            lltype.free(sval_ptr, flavor='raw')

    def gettimeofday():
        now = lltype.malloc(TIMEVALP.TO, 1, flavor='raw')
        try:
            res = _gettimeofday(now, None)
            if res < 0:
                raise OSError(rposix.get_errno(), "gettimeofday failed")
            return now[0].c_tv_sec, now[0].c_tv_usec
        finally:
            lltype.free(now, flavor='raw')

    def handle_w(space, w_handle):
        return rffi.cast(SEM_T, space.uint_w(w_handle))

    class GlobalState:
        def init(self):
            pass

        def startup(self, space):
            pass

globalState = GlobalState()

class CounterState:
    def __init__(self, space):
        self.counter = 0

    def _freeze_(self):
        self.counter = 0
        globalState.init()

    def startup(self, space):
        globalState.startup(space)

    def getCount(self):
        value = self.counter
        self.counter += 1
        return value

if sys.platform == 'win32':
    def create_semaphore(space, name, val, max):
        rwin32.SetLastError(0)
        handle = _CreateSemaphore(rffi.NULL, val, max, rffi.NULL)
        # On Windows we should fail on ERROR_ALREADY_EXISTS
        err = rwin32.GetLastError()
        if err != 0:
            raise wrap_windowserror(
                space, WindowsError(err, "CreateSemaphore"))
        return handle

    def semlock_acquire(self, space, block, w_timeout):
        if not block:
            full_msecs = 0
        elif space.is_w(w_timeout, space.w_None):
            full_msecs = rwin32.INFINITE
        else:
            timeout = space.float_w(w_timeout)
            timeout *= 1000.0
            if timeout < 0.0:
                timeout = 0.0
            elif timeout >= 0.5 * rwin32.INFINITE: # 25 days
                raise OperationError(space.w_OverflowError,
                                     space.wrap("timeout is too large"))
            full_msecs = int(timeout + 0.5)

        # check whether we can acquire without blocking
        try:
            res = rwin32.WaitForSingleObject(self.handle, 0)
        except WindowsError, e:
            raise wrap_windowserror(space, e)

        if res != rwin32.WAIT_TIMEOUT:
            return True

        msecs = r_uint(full_msecs)
        start = _GetTickCount()

        while True:
            handles = [self.handle, globalState.sigint_event]

            # do the wait
            _ResetEvent(globalState.sigint_event)
            try:
                res = rwin32.WaitForMultipleObjects(handles, timeout=msecs)
            except WindowsError, e:
                raise wrap_windowserror(space, e)

            if res != rwin32.WAIT_OBJECT_0 + 1:
                break

            # got SIGINT so give signal handler a chance to run
            time.sleep(0.001)

            # if this is main thread let KeyboardInterrupt be raised
            # XXX PyErr_CheckSignals()

            # recalculate timeout
            if msecs != rwin32.INFINITE:
                ticks = _GetTickCount()
                if r_uint(ticks - start) >= full_msecs:
                    return False
                msecs = r_uint(full_msecs - (ticks - start))

        # handle result
        if res != rwin32.WAIT_TIMEOUT:
            return True
        return False

    def semlock_release(self, space):
        if not _ReleaseSemaphore(self.handle, 1,
                                 lltype.nullptr(rffi.LONGP.TO)):
            err = rwin32.GetLastError()
            if err == 0x0000012a: # ERROR_TOO_MANY_POSTS
                raise OperationError(
                    space.w_ValueError,
                    space.wrap("semaphore or lock released too many times"))
            else:
                raise wrap_windowserror(
                    space, WindowsError(err, "ReleaseSemaphore"))

else:
    def create_semaphore(space, name, val, max):
        sem = sem_open(name, os.O_CREAT | os.O_EXCL, 0600, val)
        try:
            sem_unlink(name)
        except OSError:
            pass
        return sem

    def semlock_acquire(self, space, block, w_timeout):
        if not block:
            deadline = lltype.nullptr(TIMESPECP.TO)
        elif space.is_w(w_timeout, space.w_None):
            deadline = lltype.nullptr(TIMESPECP.TO)
        else:
            timeout = space.float_w(w_timeout)
            sec = int(timeout)
            nsec = int(1e9 * (timeout - sec) + 0.5)

            now_sec, now_usec = gettimeofday()

            deadline = lltype.malloc(TIMESPECP.TO, 1, flavor='raw')
            deadline[0].c_tv_sec = now_sec + sec
            deadline[0].c_tv_nsec = now_usec * 1000 + nsec
            deadline[0].c_tv_sec += (deadline[0].c_tv_nsec / 1000000000)
            deadline[0].c_tv_nsec %= 1000000000
        try:
            while True:
                try:
                    if not block:
                        sem_trywait(self.handle)
                    elif not deadline:
                        sem_wait(self.handle)
                    else:
                        sem_timedwait(self.handle, deadline)
                except OSError, e:
                    if e.errno == errno.EINTR:
                        # again
                        continue
                    elif e.errno in (errno.EAGAIN, errno.ETIMEDOUT):
                        return False
                    raise wrap_oserror(space, e)
                # XXX PyErr_CheckSignals()

                return True
        finally:
            if deadline:
                lltype.free(deadline, flavor='raw')


    def semlock_release(self, space):
        if self.kind == RECURSIVE_MUTEX:
            return
        if HAVE_BROKEN_SEM_GETVALUE:
            # We will only check properly the maxvalue == 1 case
            if self.maxvalue == 1:
                # make sure that already locked
                try:
                    sem_trywait(self.handle)
                except OSError, e:
                    if e.errno != errno.EAGAIN:
                        raise
                    # it is already locked as expected
                else:
                    # it was not locked so undo wait and raise
                    sem_post(self.handle)
                    raise OperationError(
                        space.w_ValueError, space.wrap(
                            "semaphore or lock released too many times"))
        else:
            # This check is not an absolute guarantee that the semaphore does
            # not rise above maxvalue.
            if sem_getvalue(self.handle) >= self.maxvalue:
                raise OperationError(
                    space.w_ValueError, space.wrap(
                    "semaphore or lock released too many times"))

        sem_post(self.handle)


class W_SemLock(Wrappable):
    def __init__(self, handle, kind, maxvalue):
        self.handle = handle
        self.kind = kind
        self.count = 0
        self.maxvalue = maxvalue

    def kind_get(space, self):
        return space.newint(self.kind)
    def maxvalue_get(space, self):
        return space.newint(self.maxvalue)
    def handle_get(space, self):
        return w_handle(space, self.handle)

    @unwrap_spec('self', ObjSpace)
    def get_count(self, space):
        return space.wrap(self.count)

    def _ismine(self):
        return self.count > 0 and ll_thread.get_ident() == self.last_tid

    @unwrap_spec('self', ObjSpace)
    def is_mine(self, space):
        return space.wrap(self._ismine())

    @unwrap_spec('self', ObjSpace, bool, W_Root)
    def acquire(self, space, block=True, w_timeout=None):
        # check whether we already own the lock
        if self.kind == RECURSIVE_MUTEX and self._ismine():
            self.count += 1
            return space.w_True

        if semlock_acquire(self, space, block, w_timeout):
            self.last_tid = ll_thread.get_ident()
            self.count += 1
            return space.w_True
        else:
            return space.w_False

    @unwrap_spec('self', ObjSpace)
    def release(self, space):
        if self.kind == RECURSIVE_MUTEX:
            if not self._ismine():
                raise OperationError(
                    space.w_AssertionError,
                    space.wrap("attempt to release recursive lock"
                               " not owned by thread"))
            if self.count > 1:
                self.count -= 1
                return

        semlock_release(self, space)

        self.count -= 1

    @unwrap_spec(ObjSpace, W_Root, W_Root, int, int)
    def rebuild(space, w_cls, w_handle, kind, maxvalue):
        self = space.allocate_instance(W_SemLock, w_cls)
        self.__init__(handle_w(space, w_handle), kind, maxvalue)
        return space.wrap(self)

@unwrap_spec(ObjSpace, W_Root, int, int, int)
def descr_new(space, w_subtype, kind, value, maxvalue):
    if kind != RECURSIVE_MUTEX and kind != SEMAPHORE:
        raise OperationError(space.w_ValueError,
                             space.wrap("unrecognized kind"))

    counter = space.fromcache(CounterState).getCount()
    name = "/mp%d-%d" % (os.getpid(), counter)

    handle = create_semaphore(space, name, value, maxvalue)

    self = space.allocate_instance(W_SemLock, w_subtype)
    self.__init__(handle, kind, maxvalue)

    return space.wrap(self)

W_SemLock.typedef = TypeDef(
    "SemLock",
    __new__ = interp2app(descr_new),
    kind = GetSetProperty(W_SemLock.kind_get),
    maxvalue = GetSetProperty(W_SemLock.maxvalue_get),
    handle = GetSetProperty(W_SemLock.handle_get),
    _count = interp2app(W_SemLock.get_count),
    _is_mine = interp2app(W_SemLock.is_mine),
    acquire = interp2app(W_SemLock.acquire),
    release = interp2app(W_SemLock.release),
    _rebuild = interp2app(W_SemLock.rebuild.im_func, as_classmethod=True),
    SEM_VALUE_MAX=SEM_VALUE_MAX,
    )
