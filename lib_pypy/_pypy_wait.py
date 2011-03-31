from ctypes import CDLL, c_int, POINTER, byref
from ctypes.util import find_library
from resource import _struct_rusage, struct_rusage

libc = CDLL(find_library("c"))
wait3 = libc.wait3

wait3.argtypes = [POINTER(c_int), c_int, POINTER(_struct_rusage)]

def wait3(options):
    status = c_int()
    _rusage = _struct_rusage()
    pid = wait3(byref(status), c_int(options), byref(_rusage))

    rusage = struct_rusage((
        float(_rusage.ru_utime),
        float(_rusage.ru_stime),
        _rusage.ru_maxrss,
        _rusage.ru_ixrss,
        _rusage.ru_idrss,
        _rusage.ru_isrss,
        _rusage.ru_minflt,
        _rusage.ru_majflt,
        _rusage.ru_nswap,
        _rusage.ru_inblock,
        _rusage.ru_oublock,
        _rusage.ru_msgsnd,
        _rusage.ru_msgrcv,
        _rusage.ru_nsignals,
        _rusage.ru_nvcsw,
        _rusage.ru_nivcsw))

    return pid, status.value, rusage

__all__ = ["wait3"]
