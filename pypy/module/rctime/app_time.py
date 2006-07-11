import os

_POSIX = os.name == "posix"

class struct_time(object):
    def __init__(self, tup):
        if tup and len(tup) < 9:
            raise TypeError, "time.struct_time() takes a 9-sequence"
        if not tup:
            raise TypeError, "time.struct_time() takes at least 1 argument (0 given)"

        self._tup = tup
        self.tm_year = self._tup[0]
        self.tm_mon = self._tup[1]
        self.tm_mday = self._tup[2]
        self.tm_hour = self._tup[3]
        self.tm_min = self._tup[4]
        self.tm_sec = self._tup[5]
        self.tm_wday = self._tup[6]
        self.tm_yday = self._tup[7]
        self.tm_isdst = self._tup[8]

    def __repr__(self):
        return "(%d, %d, %d, %d, %d, %d, %d, %d, %d)" %\
               (self.tm_year, self.tm_mon, self.tm_mday, self.tm_hour,
                self.tm_min, self.tm_sec, self.tm_wday, self.tm_yday,
                self.tm_isdst)

    def __len__(self):
        return 9

    def __getitem__(self, key):
        if not isinstance(key, (int, slice)):
            raise TypeError, "sequence index must be integer"
        return self._tup[key]

    def __cmp__(self, other):
        if isinstance(other, struct_time):
            return cmp(self._tup, other._tup)
        return cmp(self._tup, other)


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

