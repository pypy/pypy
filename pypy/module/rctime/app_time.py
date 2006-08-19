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

if _POSIX:
    def _float_sleep(secs):
        import select
        select.select([], [], [], secs)
    
    def sleep(secs):
        """sleep(seconds)
    
        Delay execution for a given number of seconds.  The argument may be
        a floating point number for subsecond precision."""
        _check_float(secs)
        _float_sleep(secs)

    
def strptime(string, format="%a %b %d %H:%M:%S %Y"):
    """strptime(string, format) -> struct_time

    Parse a string to a time tuple according to a format specification.
    See the library reference manual for formatting codes
    (same as strftime())."""

    import _strptime
    return _strptime.strptime(string, format)

__doc__ = """This module provides various functions to manipulate time values.

There are two standard representations of time.  One is the number
of seconds since the Epoch, in UTC (a.k.a. GMT).  It may be an integer
or a floating point number (to represent fractions of seconds).
The Epoch is system-defined; on Unix, it is generally January 1st, 1970.
The actual value can be retrieved by calling gmtime(0).

The other representation is a tuple of 9 integers giving local time.
The tuple items are:
  year (four digits, e.g. 1998)
  month (1-12)
  day (1-31)
  hours (0-23)
  minutes (0-59)
  seconds (0-59)
  weekday (0-6, Monday is 0)
  Julian day (day in the year, 1-366)
  DST (Daylight Savings Time) flag (-1, 0 or 1)
If the DST flag is 0, the time is given in the regular time zone;
if it is 1, the time is given in the DST time zone;
if it is -1, mktime() should guess based on the date and time.

Variables:

timezone -- difference in seconds between UTC and local standard time
altzone -- difference in  seconds between UTC and local DST time
daylight -- whether local time should reflect DST
tzname -- tuple of (standard time zone name, DST time zone name)

Functions:

time() -- return current time in seconds since the Epoch as a float
clock() -- return CPU time since process start as a float
sleep() -- delay for a number of seconds given as a float
gmtime() -- convert seconds since Epoch to UTC tuple
localtime() -- convert seconds since Epoch to local time tuple
asctime() -- convert time tuple to string
ctime() -- convert time in seconds to string
mktime() -- convert local time tuple to seconds since Epoch
strftime() -- convert time tuple to string according to format specification
strptime() -- parse string to time tuple according to format specification
tzset() -- change the local timezone"""

