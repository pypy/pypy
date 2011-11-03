"""
Utilities to get environ variables and platform-specific memory-related values.
"""
import os, sys
from pypy.rlib.rarithmetic import r_uint
from pypy.rlib.debug import debug_print, debug_start, debug_stop
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rpython.lltypesystem.lloperation import llop

# ____________________________________________________________
# Reading env vars.  Supports returning ints, uints or floats,
# and in the first two cases accepts the suffixes B, KB, MB and GB
# (lower case or upper case).

def _read_float_and_factor_from_env(varname):
    value = os.environ.get(varname)
    if value:
        if len(value) > 1 and value[-1] in 'bB':
            value = value[:-1]
        realvalue = value[:-1]
        if value[-1] in 'kK':
            factor = 1024
        elif value[-1] in 'mM':
            factor = 1024*1024
        elif value[-1] in 'gG':
            factor = 1024*1024*1024
        else:
            factor = 1
            realvalue = value
        try:
            return (float(realvalue), factor)
        except ValueError:
            pass
    return (0.0, 0)

def read_from_env(varname):
    value, factor = _read_float_and_factor_from_env(varname)
    return int(value * factor)

def read_uint_from_env(varname):
    value, factor = _read_float_and_factor_from_env(varname)
    return r_uint(value * factor)

def read_float_from_env(varname):
    value, factor = _read_float_and_factor_from_env(varname)
    if factor != 1:
        return 0.0
    return value


# ____________________________________________________________
# Get the total amount of RAM installed in a system.
# On 32-bit systems, it will try to return at most the addressable size.
# If unknown, it will just return the addressable size, which
# will be huge on 64-bit systems.

if sys.maxint == 2147483647:    # 32-bit
    if sys.platform.startswith('linux'):
        addressable_size = float(2**32)     # 4GB
    elif sys.platform == 'win32':
        addressable_size = float(2**31)     # 2GB
    else:
        addressable_size = float(2**31 + 2**30)   # 3GB (compromise)
else:
    addressable_size = float(2**63)    # 64-bit


def get_total_memory_linux(filename):
    debug_start("gc-hardware")
    result = -1.0
    try:
        fd = os.open(filename, os.O_RDONLY, 0644)
        try:
            buf = os.read(fd, 4096)
        finally:
            os.close(fd)
    except OSError:
        pass
    else:
        if buf.startswith('MemTotal:'):
            start = _skipspace(buf, len('MemTotal:'))
            stop = start
            while stop < len(buf) and buf[stop].isdigit():
                stop += 1
            if start < stop:
                result = float(buf[start:stop]) * 1024.0   # assume kB
    if result < 0.0:
        debug_print("get_total_memory() failed")
        result = addressable_size
    else:
        debug_print("memtotal =", result)
        if result > addressable_size:
            result = addressable_size
    debug_stop("gc-hardware")
    return result
get_total_memory_linux2 = get_total_memory_linux3 = get_total_memory_linux

def get_total_memory_darwin(result):
    debug_start("gc-hardware")
    if result <= 0:
        debug_print("get_total_memory() failed")
        result = addressable_size
    else:
        debug_print("memtotal = ", result)
        if result > addressable_size:
            result = addressable_size
    debug_stop("gc-hardware")
    return result


if sys.platform.startswith('linux'):
    def get_total_memory():
        return get_total_memory_linux2('/proc/meminfo')

elif sys.platform == 'darwin':
    def get_total_memory():
        return get_total_memory_darwin(get_darwin_sysctl_signed('hw.memsize'))

elif sys.platform.startswith('freebsd'):
    def get_total_memory():
        return get_total_memory_darwin(get_darwin_sysctl_signed('hw.usermem'))

else:
    def get_total_memory():
        return addressable_size       # XXX implement me for other platforms


# ____________________________________________________________
# Estimation of the nursery size, based on the L2 cache.

# ---------- Linux2 ----------

def get_L2cache_linux2(filename="/proc/cpuinfo"):
    debug_start("gc-hardware")
    L2cache = sys.maxint
    try:
        fd = os.open(filename, os.O_RDONLY, 0644)
        try:
            data = []
            while True:
                buf = os.read(fd, 4096)
                if not buf:
                    break
                data.append(buf)
        finally:
            os.close(fd)
    except OSError:
        pass
    else:
        data = ''.join(data)
        linepos = 0
        while True:
            start = _findend(data, '\ncache size', linepos)
            if start < 0:
                break    # done
            linepos = _findend(data, '\n', start)
            if linepos < 0:
                break    # no end-of-line??
            # *** data[start:linepos] == "   : 2048 KB\n"
            start = _skipspace(data, start)
            if data[start] != ':':
                continue
            # *** data[start:linepos] == ": 2048 KB\n"
            start = _skipspace(data, start + 1)
            # *** data[start:linepos] == "2048 KB\n"
            end = start
            while '0' <= data[end] <= '9':
                end += 1
            # *** data[start:end] == "2048"
            if start == end:
                continue
            number = int(data[start:end])
            # *** data[end:linepos] == " KB\n"
            end = _skipspace(data, end)
            if data[end] not in ('K', 'k'):    # assume kilobytes for now
                continue
            number = number * 1024
            # for now we look for the smallest of the L2 caches of the CPUs
            if number < L2cache:
                L2cache = number

    debug_print("L2cache =", L2cache)
    debug_stop("gc-hardware")

    if L2cache < sys.maxint:
        return L2cache
    else:
        # Print a top-level warning even in non-debug builds
        llop.debug_print(lltype.Void,
            "Warning: cannot find your CPU L2 cache size in /proc/cpuinfo")
        return -1

def _findend(data, pattern, pos):
    pos = data.find(pattern, pos)
    if pos < 0:
        return -1
    return pos + len(pattern)

def _skipspace(data, pos):
    while data[pos] in (' ', '\t'):
        pos += 1
    return pos

# ---------- Darwin ----------

sysctlbyname = rffi.llexternal('sysctlbyname',
                               [rffi.CCHARP, rffi.VOIDP, rffi.SIZE_TP,
                                rffi.VOIDP, rffi.SIZE_T],
                               rffi.INT,
                               sandboxsafe=True)

def get_darwin_sysctl_signed(sysctl_name):
    rval_p = lltype.malloc(rffi.LONGLONGP.TO, 1, flavor='raw')
    try:
        len_p = lltype.malloc(rffi.SIZE_TP.TO, 1, flavor='raw')
        try:
            size = rffi.sizeof(rffi.LONGLONG)
            rval_p[0] = rffi.cast(rffi.LONGLONG, 0)
            len_p[0] = rffi.cast(rffi.SIZE_T, size)
            # XXX a hack for llhelper not being robust-enough
            result = sysctlbyname(sysctl_name,
                                  rffi.cast(rffi.VOIDP, rval_p),
                                  len_p,
                                  lltype.nullptr(rffi.VOIDP.TO),
                                  rffi.cast(rffi.SIZE_T, 0))
            rval = 0
            if (rffi.cast(lltype.Signed, result) == 0 and
                rffi.cast(lltype.Signed, len_p[0]) == size):
                rval = rffi.cast(lltype.Signed, rval_p[0])
                if rffi.cast(rffi.LONGLONG, rval) != rval_p[0]:
                    rval = 0    # overflow!
            return rval
        finally:
            lltype.free(len_p, flavor='raw')
    finally:
        lltype.free(rval_p, flavor='raw')


def get_L2cache_darwin():
    """Try to estimate the best nursery size at run-time, depending
    on the machine we are running on.
    """
    debug_start("gc-hardware")
    L2cache = get_darwin_sysctl_signed("hw.l2cachesize")
    L3cache = get_darwin_sysctl_signed("hw.l3cachesize")
    debug_print("L2cache =", L2cache)
    debug_print("L3cache =", L3cache)
    debug_stop("gc-hardware")

    mangled = L2cache + L3cache

    if mangled > 0:
        return mangled
    else:
        # Print a top-level warning even in non-debug builds
        llop.debug_print(lltype.Void,
            "Warning: cannot find your CPU L2 cache size with sysctl()")
        return -1


# --------------------

get_L2cache = globals().get('get_L2cache_' + sys.platform,
                            lambda: -1)     # implement me for other platforms

NURSERY_SIZE_UNKNOWN_CACHE = 1024*1024
# arbitrary 1M. better than default of 131k for most cases
# in case it didn't work

def best_nursery_size_for_L2cache(L2cache):
    # Heuristically, the best nursery size to choose is about half
    # of the L2 cache.
    if L2cache > 0:
        return L2cache // 2
    else:
        return NURSERY_SIZE_UNKNOWN_CACHE

def estimate_best_nursery_size():
    """Try to estimate the best nursery size at run-time, depending
    on the machine we are running on.  Linux code."""
    L2cache = get_L2cache()
    return best_nursery_size_for_L2cache(L2cache)
