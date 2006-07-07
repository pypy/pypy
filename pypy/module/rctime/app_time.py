import os

_POSIX = os.name == "posix"

def _check_float(arg):
    try:
        float(arg)
    except ValueError:
        raise TypeError, "a float is required"

def _float_sleep(secs):
    import select
    
    if _POSIX:
        select.select([], [], [], secs)
        return
    # elif _MS_WINDOWS:
    #     msecs = secs * 1000.0
    #     if msecs > float(sys.maxint * 2 - 1): # ULONG_MAX
    #         raise OverflowError, "sleep length is too large"
    #     lock.acquire()
    #     ul_millis = c_ulong(long(msecs))
    #     windll.kernel32.Sleep(ul_millis)
    #     lock.release()
    # else:
    #     lock.acquire()
    #     _libc.sleep.argtypes = [c_int]
    #     _libc.sleep(int(secs))
    #     lock.release()

def sleep(secs):
    _check_float(secs)
    _float_sleep(secs)

