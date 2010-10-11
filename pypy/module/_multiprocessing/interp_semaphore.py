from pypy.interpreter.baseobjspace import ObjSpace, Wrappable, W_Root
from pypy.interpreter.typedef import TypeDef, GetSetProperty
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.error import (
    wrap_windowserror, wrap_oserror, OperationError)
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib.rarithmetic import r_uint
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.module.thread import ll_thread
import sys, os, time

RECURSIVE_MUTEX, SEMAPHORE = range(2)

if sys.platform == 'win32':
    from pypy.rlib import rwin32

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
    # callinf convention, which is not supported by lltype.Ptr.
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
    SEM_VALUE_MAX = sys.maxint
    from pypy.module._multiprocessing.interp_win32 import w_handle

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
            self.last_tid = ll_thread.get_ident()
            self.count += 1
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
            self.last_tid = ll_thread.get_ident()
            self.count += 1
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
    HAVE_BROKEN_SEM_GETVALUE = False

    def create_semaphore(space, name, val, max):
        sem_open(name, os.O_CREAT | os.O_EXCL, 0600, val)
        sem_unlink(name)

    def semlock_acquire(self, space, block, w_timeout):
        if not block:
            deadline = lltype.nullptr(TIMESPEC.TO)
        elif space.is_w(w_timeout, space.w_None):
            deadline = lltype.nullptr(TIMESPEC.TO)
        else:
            timeout = space.float_w(w_timeout)
            sec = int(timeout)
            nsec = int(1e9 * (timeout - sec) + 0.5)

            deadline = lltype.malloc(TIMESPEC.TO, 1, flavor='raw')
            deadline.c_tv_sec = now.c_tv_sec + sec
            deadline.c_tv_nsec = now.c_tv_usec * 1000 + nsec
            deadline.c_tv_sec += (deadline.c_tv_nsec / 1000000000)
            deadline.c_tv_nsec %= 1000000000
        try:
            while True:
                if not block:
                    res = sem_trywait(self.handle)
                elif not deadline:
                    res = sem_wait(self.handle)
                else:
                    res = sem_timedwait(self.handle, deadline)
                if res >= 0:
                    break
                elif errno != EINTR:
                    break
                # elif PyErr_CheckSignals():
                #     raise...
        finally:
            if deadline:
                lltype.free(deadline, flavor='raw')

        if res < 0:
            if errno == EAGAIN or errno == ETIMEDOUT:
                return False
            raise wrap_oserror(space, errno)
        return True

    def semlock_release(self, space):
        if self.kind == RECURSIVE_MUTEX:
            return
        if HAVE_BROKEN_SEM_GETVALUE:
            # We will only check properly the maxvalue == 1 case
            if self.maxvalue == 1:
                # make sure that already locked
                if sem_trywait(self.handle) < 0:
                    if errno != EAGAIN:
                        raise
                    # it is already locked as expected
                else:
                    # it was not locked so undo wait and raise
                    if sem_post(self.handle) < 0:
                        raise
                    raise OperationError(
                        space.w_ValueError, space.wrap(
                            "semaphore or lock released too many times"))
        else:
            # This check is not an absolute guarantee that the semaphore does
            # not rise above maxvalue.
            if sem_getvalue(self.handle, sval_ptr) < 0:
                raise
            if sval_ptr[0] >= self.maxvalue:
                    raise OperationError(
                        space.w_ValueError, space.wrap(
                            "semaphore or lock released too many times"))

        if sem_post(self.handle) < 0:
            raise


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

        res = semlock_acquire(self, space, block, w_timeout)
        return space.wrap(res)

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
    SEM_VALUE_MAX=SEM_VALUE_MAX,
    )
