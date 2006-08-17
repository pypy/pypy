from ctypes import *
STRING = c_char_p


P_ALL = 0
OSUnknownByteOrder = 0
OSBigEndian = 2
_FP_NAN = 1
_FP_INFINITE = 2
P_PGID = 2
_FP_NORMAL = 4
OSLittleEndian = 1
P_PID = 1
_FP_SUBNORMAL = 5
_FP_SUPERNORMAL = 6
_FP_ZERO = 3
__darwin_nl_item = c_int
__darwin_wctrans_t = c_int
__darwin_wctype_t = c_ulong
float_t = c_float
double_t = c_double

# values for unnamed enumeration
__int8_t = c_byte
__uint8_t = c_ubyte
__int16_t = c_short
__uint16_t = c_ushort
__int32_t = c_int
__uint32_t = c_uint
__int64_t = c_longlong
__uint64_t = c_ulonglong
__darwin_intptr_t = c_long
__darwin_natural_t = c_uint
__darwin_ct_rune_t = c_int
class __mbstate_t(Union):
    pass
__mbstate_t._pack_ = 4
__mbstate_t._fields_ = [
    ('__mbstate8', c_char * 128),
    ('_mbstateL', c_longlong),
]
assert sizeof(__mbstate_t) == 128, sizeof(__mbstate_t)
assert alignment(__mbstate_t) == 4, alignment(__mbstate_t)
__darwin_mbstate_t = __mbstate_t
__darwin_ptrdiff_t = c_int
__darwin_size_t = c_ulong
__darwin_va_list = STRING
__darwin_wchar_t = c_int
__darwin_rune_t = __darwin_wchar_t
__darwin_wint_t = c_int
__darwin_clock_t = c_ulong
__darwin_socklen_t = __uint32_t
__darwin_ssize_t = c_long
__darwin_time_t = c_long
sig_atomic_t = c_int
class sigcontext(Structure):
    pass
sigcontext._fields_ = [
    ('sc_onstack', c_int),
    ('sc_mask', c_int),
    ('sc_eax', c_uint),
    ('sc_ebx', c_uint),
    ('sc_ecx', c_uint),
    ('sc_edx', c_uint),
    ('sc_edi', c_uint),
    ('sc_esi', c_uint),
    ('sc_ebp', c_uint),
    ('sc_esp', c_uint),
    ('sc_ss', c_uint),
    ('sc_eflags', c_uint),
    ('sc_eip', c_uint),
    ('sc_cs', c_uint),
    ('sc_ds', c_uint),
    ('sc_es', c_uint),
    ('sc_fs', c_uint),
    ('sc_gs', c_uint),
]
assert sizeof(sigcontext) == 72, sizeof(sigcontext)
assert alignment(sigcontext) == 4, alignment(sigcontext)
int8_t = c_byte
u_int8_t = c_ubyte
int16_t = c_short
u_int16_t = c_ushort
int32_t = c_int
u_int32_t = c_uint
int64_t = c_longlong
u_int64_t = c_ulonglong
register_t = int32_t
intptr_t = __darwin_intptr_t
uintptr_t = c_ulong
user_addr_t = u_int64_t
user_size_t = u_int64_t
user_ssize_t = int64_t
user_long_t = int64_t
user_ulong_t = u_int64_t
user_time_t = int64_t
syscall_arg_t = u_int64_t

# values for unnamed enumeration
va_list = __darwin_va_list
size_t = __darwin_size_t
__darwin_off_t = __int64_t
fpos_t = __darwin_off_t
class __sbuf(Structure):
    pass
__sbuf._fields_ = [
    ('_base', POINTER(c_ubyte)),
    ('_size', c_int),
]
__sbuf.__name__ = "__sbuf_"
assert sizeof(__sbuf) == 8, sizeof(__sbuf)
assert alignment(__sbuf) == 4, alignment(__sbuf)
class __sFILEX(Structure):
    pass
__sFILEX._fields_ = []
class __sFILE(Structure):
    pass
__sFILE._pack_ = 4
__sFILE._fields_ = [
    ('_p', POINTER(c_ubyte)),
    ('_r', c_int),
    ('_w', c_int),
    ('_flags', c_short),
    ('_file', c_short),
    ('_bf', __sbuf),
    ('_lbfsize', c_int),
    ('_cookie', c_void_p),
    ('_close', CFUNCTYPE(c_int, c_void_p)),
    ('_read', CFUNCTYPE(c_int, c_void_p, STRING, c_int)),
    ('_seek', CFUNCTYPE(fpos_t, c_void_p, c_longlong, c_int)),
    ('_write', CFUNCTYPE(c_int, c_void_p, STRING, c_int)),
    ('_ub', __sbuf),
    ('_extra', POINTER(__sFILEX)),
    ('_ur', c_int),
    ('_ubuf', c_ubyte * 3),
    ('_nbuf', c_ubyte * 1),
    ('_lb', __sbuf),
    ('_blksize', c_int),
    ('_offset', fpos_t),
]
__sFILE.__name__ = "__sFILE_"
assert sizeof(__sFILE) == 88, sizeof(__sFILE)
assert alignment(__sFILE) == 4, alignment(__sFILE)
FILE = __sFILE
ct_rune_t = __darwin_ct_rune_t
rune_t = __darwin_rune_t
class div_t(Structure):
    pass
div_t._fields_ = [
    ('quot', c_int),
    ('rem', c_int),
]
assert sizeof(div_t) == 8, sizeof(div_t)
assert alignment(div_t) == 4, alignment(div_t)
class ldiv_t(Structure):
    pass
ldiv_t._fields_ = [
    ('quot', c_long),
    ('rem', c_long),
]
assert sizeof(ldiv_t) == 8, sizeof(ldiv_t)
assert alignment(ldiv_t) == 4, alignment(ldiv_t)
class lldiv_t(Structure):
    pass
lldiv_t._pack_ = 4
lldiv_t._fields_ = [
    ('quot', c_longlong),
    ('rem', c_longlong),
]
assert sizeof(lldiv_t) == 16, sizeof(lldiv_t)
assert alignment(lldiv_t) == 4, alignment(lldiv_t)
class mcontext(Structure):
    pass
class mcontext64(Structure):
    pass
class __darwin_pthread_handler_rec(Structure):
    pass
__darwin_pthread_handler_rec._fields_ = [
    ('__routine', CFUNCTYPE(None, c_void_p)),
    ('__arg', c_void_p),
    ('__next', POINTER(__darwin_pthread_handler_rec)),
]
assert sizeof(__darwin_pthread_handler_rec) == 12, sizeof(__darwin_pthread_handler_rec)
assert alignment(__darwin_pthread_handler_rec) == 4, alignment(__darwin_pthread_handler_rec)
class _opaque_pthread_attr_t(Structure):
    pass
_opaque_pthread_attr_t._fields_ = [
    ('__sig', c_long),
    ('__opaque', c_char * 36),
]
assert sizeof(_opaque_pthread_attr_t) == 40, sizeof(_opaque_pthread_attr_t)
assert alignment(_opaque_pthread_attr_t) == 4, alignment(_opaque_pthread_attr_t)
class _opaque_pthread_cond_t(Structure):
    pass
_opaque_pthread_cond_t._fields_ = [
    ('__sig', c_long),
    ('__opaque', c_char * 24),
]
assert sizeof(_opaque_pthread_cond_t) == 28, sizeof(_opaque_pthread_cond_t)
assert alignment(_opaque_pthread_cond_t) == 4, alignment(_opaque_pthread_cond_t)
class _opaque_pthread_condattr_t(Structure):
    pass
_opaque_pthread_condattr_t._fields_ = [
    ('__sig', c_long),
    ('__opaque', c_char * 4),
]
assert sizeof(_opaque_pthread_condattr_t) == 8, sizeof(_opaque_pthread_condattr_t)
assert alignment(_opaque_pthread_condattr_t) == 4, alignment(_opaque_pthread_condattr_t)
class _opaque_pthread_mutex_t(Structure):
    pass
_opaque_pthread_mutex_t._fields_ = [
    ('__sig', c_long),
    ('__opaque', c_char * 40),
]
assert sizeof(_opaque_pthread_mutex_t) == 44, sizeof(_opaque_pthread_mutex_t)
assert alignment(_opaque_pthread_mutex_t) == 4, alignment(_opaque_pthread_mutex_t)
class _opaque_pthread_mutexattr_t(Structure):
    pass
_opaque_pthread_mutexattr_t._fields_ = [
    ('__sig', c_long),
    ('__opaque', c_char * 8),
]
assert sizeof(_opaque_pthread_mutexattr_t) == 12, sizeof(_opaque_pthread_mutexattr_t)
assert alignment(_opaque_pthread_mutexattr_t) == 4, alignment(_opaque_pthread_mutexattr_t)
class _opaque_pthread_once_t(Structure):
    pass
_opaque_pthread_once_t._fields_ = [
    ('__sig', c_long),
    ('__opaque', c_char * 4),
]
assert sizeof(_opaque_pthread_once_t) == 8, sizeof(_opaque_pthread_once_t)
assert alignment(_opaque_pthread_once_t) == 4, alignment(_opaque_pthread_once_t)
class _opaque_pthread_rwlock_t(Structure):
    pass
_opaque_pthread_rwlock_t._fields_ = [
    ('__sig', c_long),
    ('__opaque', c_char * 124),
]
assert sizeof(_opaque_pthread_rwlock_t) == 128, sizeof(_opaque_pthread_rwlock_t)
assert alignment(_opaque_pthread_rwlock_t) == 4, alignment(_opaque_pthread_rwlock_t)
class _opaque_pthread_rwlockattr_t(Structure):
    pass
_opaque_pthread_rwlockattr_t._fields_ = [
    ('__sig', c_long),
    ('__opaque', c_char * 12),
]
assert sizeof(_opaque_pthread_rwlockattr_t) == 16, sizeof(_opaque_pthread_rwlockattr_t)
assert alignment(_opaque_pthread_rwlockattr_t) == 4, alignment(_opaque_pthread_rwlockattr_t)
class _opaque_pthread_t(Structure):
    pass
_opaque_pthread_t._fields_ = [
    ('__sig', c_long),
    ('__cleanup_stack', POINTER(__darwin_pthread_handler_rec)),
    ('__opaque', c_char * 596),
]
assert sizeof(_opaque_pthread_t) == 604, sizeof(_opaque_pthread_t)
assert alignment(_opaque_pthread_t) == 4, alignment(_opaque_pthread_t)
__darwin_blkcnt_t = __int64_t
__darwin_blksize_t = __int32_t
__darwin_dev_t = __int32_t
__darwin_fsblkcnt_t = c_uint
__darwin_fsfilcnt_t = c_uint
__darwin_gid_t = __uint32_t
__darwin_id_t = __uint32_t
__darwin_ino_t = __uint32_t
__darwin_mach_port_name_t = __darwin_natural_t
__darwin_mach_port_t = __darwin_mach_port_name_t
__darwin_mcontext_t = POINTER(mcontext)
__darwin_mcontext64_t = POINTER(mcontext64)
__darwin_mode_t = __uint16_t
__darwin_pid_t = __int32_t
__darwin_pthread_attr_t = _opaque_pthread_attr_t
__darwin_pthread_cond_t = _opaque_pthread_cond_t
__darwin_pthread_condattr_t = _opaque_pthread_condattr_t
__darwin_pthread_key_t = c_ulong
__darwin_pthread_mutex_t = _opaque_pthread_mutex_t
__darwin_pthread_mutexattr_t = _opaque_pthread_mutexattr_t
__darwin_pthread_once_t = _opaque_pthread_once_t
__darwin_pthread_rwlock_t = _opaque_pthread_rwlock_t
__darwin_pthread_rwlockattr_t = _opaque_pthread_rwlockattr_t
__darwin_pthread_t = POINTER(_opaque_pthread_t)
__darwin_sigset_t = __uint32_t
__darwin_suseconds_t = __int32_t
__darwin_uid_t = __uint32_t
__darwin_useconds_t = __uint32_t
__darwin_uuid_t = c_ubyte * 16
class sigaltstack(Structure):
    pass
sigaltstack._fields_ = [
    ('ss_sp', c_void_p),
    ('ss_size', __darwin_size_t),
    ('ss_flags', c_int),
]
assert sizeof(sigaltstack) == 12, sizeof(sigaltstack)
assert alignment(sigaltstack) == 4, alignment(sigaltstack)
__darwin_stack_t = sigaltstack
class ucontext(Structure):
    pass
ucontext._fields_ = [
    ('uc_onstack', c_int),
    ('uc_sigmask', __darwin_sigset_t),
    ('uc_stack', __darwin_stack_t),
    ('uc_link', POINTER(ucontext)),
    ('uc_mcsize', __darwin_size_t),
    ('uc_mcontext', __darwin_mcontext_t),
]
assert sizeof(ucontext) == 32, sizeof(ucontext)
assert alignment(ucontext) == 4, alignment(ucontext)
__darwin_ucontext_t = ucontext
class ucontext64(Structure):
    pass
ucontext64._fields_ = [
    ('uc_onstack', c_int),
    ('uc_sigmask', __darwin_sigset_t),
    ('uc_stack', __darwin_stack_t),
    ('uc_link', POINTER(ucontext64)),
    ('uc_mcsize', __darwin_size_t),
    ('uc_mcontext64', __darwin_mcontext64_t),
]
assert sizeof(ucontext64) == 32, sizeof(ucontext64)
assert alignment(ucontext64) == 4, alignment(ucontext64)
__darwin_ucontext64_t = ucontext64
class timeval(Structure):
    pass
timeval._fields_ = [
    ('tv_sec', __darwin_time_t),
    ('tv_usec', __darwin_suseconds_t),
]
assert sizeof(timeval) == 8, sizeof(timeval)
assert alignment(timeval) == 4, alignment(timeval)
rlim_t = __int64_t
class rusage(Structure):
    pass
rusage._fields_ = [
    ('ru_utime', timeval),
    ('ru_stime', timeval),
    ('ru_maxrss', c_long),
    ('ru_ixrss', c_long),
    ('ru_idrss', c_long),
    ('ru_isrss', c_long),
    ('ru_minflt', c_long),
    ('ru_majflt', c_long),
    ('ru_nswap', c_long),
    ('ru_inblock', c_long),
    ('ru_oublock', c_long),
    ('ru_msgsnd', c_long),
    ('ru_msgrcv', c_long),
    ('ru_nsignals', c_long),
    ('ru_nvcsw', c_long),
    ('ru_nivcsw', c_long),
]
assert sizeof(rusage) == 72, sizeof(rusage)
assert alignment(rusage) == 4, alignment(rusage)
class rlimit(Structure):
    pass
rlimit._pack_ = 4
rlimit._fields_ = [
    ('rlim_cur', rlim_t),
    ('rlim_max', rlim_t),
]
assert sizeof(rlimit) == 16, sizeof(rlimit)
assert alignment(rlimit) == 4, alignment(rlimit)
mcontext_t = __darwin_mcontext_t
mcontext64_t = __darwin_mcontext64_t
sigset_t = __darwin_sigset_t
ucontext_t = __darwin_ucontext_t
ucontext64_t = __darwin_ucontext64_t
class sigval(Union):
    pass
sigval._fields_ = [
    ('sival_int', c_int),
    ('sival_ptr', c_void_p),
]
assert sizeof(sigval) == 4, sizeof(sigval)
assert alignment(sigval) == 4, alignment(sigval)
class sigevent(Structure):
    pass
pthread_attr_t = __darwin_pthread_attr_t
sigevent._fields_ = [
    ('sigev_notify', c_int),
    ('sigev_signo', c_int),
    ('sigev_value', sigval),
    ('sigev_notify_function', CFUNCTYPE(None, sigval)),
    ('sigev_notify_attributes', POINTER(pthread_attr_t)),
]
assert sizeof(sigevent) == 20, sizeof(sigevent)
assert alignment(sigevent) == 4, alignment(sigevent)
class __siginfo(Structure):
    pass
pid_t = __darwin_pid_t
uid_t = __darwin_uid_t
__siginfo._fields_ = [
    ('si_signo', c_int),
    ('si_errno', c_int),
    ('si_code', c_int),
    ('si_pid', pid_t),
    ('si_uid', uid_t),
    ('si_status', c_int),
    ('si_addr', c_void_p),
    ('si_value', sigval),
    ('si_band', c_long),
    ('pad', c_ulong * 7),
]
assert sizeof(__siginfo) == 64, sizeof(__siginfo)
assert alignment(__siginfo) == 4, alignment(__siginfo)
siginfo_t = __siginfo
class __sigaction_u(Union):
    pass
__sigaction_u._fields_ = [
    ('__sa_handler', CFUNCTYPE(None, c_int)),
    ('__sa_sigaction', CFUNCTYPE(None, c_int, POINTER(__siginfo), c_void_p)),
]
assert sizeof(__sigaction_u) == 4, sizeof(__sigaction_u)
assert alignment(__sigaction_u) == 4, alignment(__sigaction_u)
class __sigaction(Structure):
    pass
__sigaction._fields_ = [
    ('__sigaction_u', __sigaction_u),
    ('sa_tramp', CFUNCTYPE(None, c_void_p, c_int, c_int, POINTER(siginfo_t), c_void_p)),
    ('sa_mask', sigset_t),
    ('sa_flags', c_int),
]
assert sizeof(__sigaction) == 16, sizeof(__sigaction)
assert alignment(__sigaction) == 4, alignment(__sigaction)
class sigaction(Structure):
    pass
sigaction._fields_ = [
    ('__sigaction_u', __sigaction_u),
    ('sa_mask', sigset_t),
    ('sa_flags', c_int),
]
assert sizeof(sigaction) == 12, sizeof(sigaction)
assert alignment(sigaction) == 4, alignment(sigaction)
sig_t = CFUNCTYPE(None, c_int)
stack_t = __darwin_stack_t
class sigvec(Structure):
    pass
sigvec._fields_ = [
    ('sv_handler', CFUNCTYPE(None, c_int)),
    ('sv_mask', c_int),
    ('sv_flags', c_int),
]
assert sizeof(sigvec) == 12, sizeof(sigvec)
assert alignment(sigvec) == 4, alignment(sigvec)
class sigstack(Structure):
    pass
sigstack._fields_ = [
    ('ss_sp', STRING),
    ('ss_onstack', c_int),
]
assert sizeof(sigstack) == 8, sizeof(sigstack)
assert alignment(sigstack) == 4, alignment(sigstack)
class ostat(Structure):
    pass
ino_t = __darwin_ino_t
mode_t = __darwin_mode_t
nlink_t = __uint16_t
class timespec(Structure):
    pass
time_t = __darwin_time_t
timespec._fields_ = [
    ('tv_sec', time_t),
    ('tv_nsec', c_long),
]
assert sizeof(timespec) == 8, sizeof(timespec)
assert alignment(timespec) == 4, alignment(timespec)
ostat._fields_ = [
    ('st_dev', __uint16_t),
    ('st_ino', ino_t),
    ('st_mode', mode_t),
    ('st_nlink', nlink_t),
    ('st_uid', __uint16_t),
    ('st_gid', __uint16_t),
    ('st_rdev', __uint16_t),
    ('st_size', __int32_t),
    ('st_atimespec', timespec),
    ('st_mtimespec', timespec),
    ('st_ctimespec', timespec),
    ('st_blksize', __int32_t),
    ('st_blocks', __int32_t),
    ('st_flags', __uint32_t),
    ('st_gen', __uint32_t),
]
assert sizeof(ostat) == 64, sizeof(ostat)
assert alignment(ostat) == 4, alignment(ostat)
class stat(Structure):
    pass
dev_t = __darwin_dev_t
gid_t = __darwin_gid_t
off_t = __darwin_off_t
blkcnt_t = __darwin_blkcnt_t
blksize_t = __darwin_blksize_t
stat._pack_ = 4
stat._fields_ = [
    ('st_dev', dev_t),
    ('st_ino', ino_t),
    ('st_mode', mode_t),
    ('st_nlink', nlink_t),
    ('st_uid', uid_t),
    ('st_gid', gid_t),
    ('st_rdev', dev_t),
    ('st_atimespec', timespec),
    ('st_mtimespec', timespec),
    ('st_ctimespec', timespec),
    ('st_size', off_t),
    ('st_blocks', blkcnt_t),
    ('st_blksize', blksize_t),
    ('st_flags', __uint32_t),
    ('st_gen', __uint32_t),
    ('st_lspare', __int32_t),
    ('st_qspare', __int64_t * 2),
]
assert sizeof(stat) == 96, sizeof(stat)
assert alignment(stat) == 4, alignment(stat)
class _filesec(Structure):
    pass
filesec_t = POINTER(_filesec)
tcflag_t = c_ulong
cc_t = c_ubyte
speed_t = c_long
class termios(Structure):
    pass
termios._fields_ = [
    ('c_iflag', tcflag_t),
    ('c_oflag', tcflag_t),
    ('c_cflag', tcflag_t),
    ('c_lflag', tcflag_t),
    ('c_cc', cc_t * 20),
    ('c_ispeed', speed_t),
    ('c_ospeed', speed_t),
]
assert sizeof(termios) == 44, sizeof(termios)
assert alignment(termios) == 4, alignment(termios)
class itimerval(Structure):
    pass
itimerval._fields_ = [
    ('it_interval', timeval),
    ('it_value', timeval),
]
assert sizeof(itimerval) == 16, sizeof(itimerval)
assert alignment(itimerval) == 4, alignment(itimerval)
class timezone(Structure):
    pass
timezone._fields_ = [
    ('tz_minuteswest', c_int),
    ('tz_dsttime', c_int),
]
assert sizeof(timezone) == 8, sizeof(timezone)
assert alignment(timezone) == 4, alignment(timezone)
class clockinfo(Structure):
    pass
clockinfo._fields_ = [
    ('hz', c_int),
    ('tick', c_int),
    ('tickadj', c_int),
    ('stathz', c_int),
    ('profhz', c_int),
]
assert sizeof(clockinfo) == 20, sizeof(clockinfo)
assert alignment(clockinfo) == 4, alignment(clockinfo)
class winsize(Structure):
    pass
winsize._fields_ = [
    ('ws_row', c_ushort),
    ('ws_col', c_ushort),
    ('ws_xpixel', c_ushort),
    ('ws_ypixel', c_ushort),
]
assert sizeof(winsize) == 8, sizeof(winsize)
assert alignment(winsize) == 2, alignment(winsize)
u_char = c_ubyte
u_short = c_ushort
u_int = c_uint
u_long = c_ulong
ushort = c_ushort
uint = c_uint
u_quad_t = u_int64_t
quad_t = int64_t
qaddr_t = POINTER(quad_t)
caddr_t = STRING
daddr_t = int32_t
fixpt_t = u_int32_t
in_addr_t = __uint32_t
in_port_t = __uint16_t
key_t = __int32_t
id_t = __darwin_id_t
segsz_t = int32_t
swblk_t = int32_t
clock_t = __darwin_clock_t
ssize_t = __darwin_ssize_t
useconds_t = __darwin_useconds_t
suseconds_t = __darwin_suseconds_t
fd_mask = __int32_t
class fd_set(Structure):
    pass
fd_set._fields_ = [
    ('fds_bits', __int32_t * 32),
]
assert sizeof(fd_set) == 128, sizeof(fd_set)
assert alignment(fd_set) == 4, alignment(fd_set)
pthread_cond_t = __darwin_pthread_cond_t
pthread_condattr_t = __darwin_pthread_condattr_t
pthread_mutex_t = __darwin_pthread_mutex_t
pthread_mutexattr_t = __darwin_pthread_mutexattr_t
pthread_once_t = __darwin_pthread_once_t
pthread_rwlock_t = __darwin_pthread_rwlock_t
pthread_rwlockattr_t = __darwin_pthread_rwlockattr_t
pthread_t = __darwin_pthread_t
pthread_key_t = __darwin_pthread_key_t
fsblkcnt_t = __darwin_fsblkcnt_t
fsfilcnt_t = __darwin_fsfilcnt_t

# values for enumeration 'idtype_t'
idtype_t = c_int # enum
class wait(Union):
    pass
class N4wait3DOLLAR_3E(Structure):
    pass
N4wait3DOLLAR_3E._fields_ = [
    ('w_Termsig', c_uint, 7),
    ('w_Coredump', c_uint, 1),
    ('w_Retcode', c_uint, 8),
    ('w_Filler', c_uint, 16),
]
assert sizeof(N4wait3DOLLAR_3E) == 4, sizeof(N4wait3DOLLAR_3E)
assert alignment(N4wait3DOLLAR_3E) == 4, alignment(N4wait3DOLLAR_3E)
class N4wait3DOLLAR_4E(Structure):
    pass
N4wait3DOLLAR_4E._fields_ = [
    ('w_Stopval', c_uint, 8),
    ('w_Stopsig', c_uint, 8),
    ('w_Filler', c_uint, 16),
]
assert sizeof(N4wait3DOLLAR_4E) == 4, sizeof(N4wait3DOLLAR_4E)
assert alignment(N4wait3DOLLAR_4E) == 4, alignment(N4wait3DOLLAR_4E)
wait._fields_ = [
    ('w_status', c_int),
    ('w_T', N4wait3DOLLAR_3E),
    ('w_S', N4wait3DOLLAR_4E),
]
assert sizeof(wait) == 4, sizeof(wait)
assert alignment(wait) == 4, alignment(wait)
class tm(Structure):
    pass
tm._fields_ = [
    ('tm_sec', c_int),
    ('tm_min', c_int),
    ('tm_hour', c_int),
    ('tm_mday', c_int),
    ('tm_mon', c_int),
    ('tm_year', c_int),
    ('tm_wday', c_int),
    ('tm_yday', c_int),
    ('tm_isdst', c_int),
    ('tm_gmtoff', c_long),
    ('tm_zone', STRING),
]
assert sizeof(tm) == 44, sizeof(tm)
assert alignment(tm) == 4, alignment(tm)
uint8_t = c_ubyte
uint16_t = c_ushort
uint32_t = c_uint
uint64_t = c_ulonglong
int_least8_t = int8_t
int_least16_t = int16_t
int_least32_t = int32_t
int_least64_t = int64_t
uint_least8_t = uint8_t
uint_least16_t = uint16_t
uint_least32_t = uint32_t
uint_least64_t = uint64_t
int_fast8_t = int8_t
int_fast16_t = int16_t
int_fast32_t = int32_t
int_fast64_t = int64_t
uint_fast8_t = uint8_t
uint_fast16_t = uint16_t
uint_fast32_t = uint32_t
uint_fast64_t = uint64_t
intmax_t = c_longlong
uintmax_t = c_ulonglong
class PyFileObject(Structure):
    pass
Py_ssize_t = ssize_t
class _typeobject(Structure):
    pass
class _object(Structure):
    pass
_object.__name__ = "_object_"
PyObject = _object
PyFileObject._fields_ = [
    ('ob_refcnt', Py_ssize_t),
    ('ob_type', POINTER(_typeobject)),
    ('f_fp', POINTER(FILE)),
    ('f_name', POINTER(PyObject)),
    ('f_mode', POINTER(PyObject)),
    ('f_close', CFUNCTYPE(c_int, POINTER(FILE))),
    ('f_softspace', c_int),
    ('f_binary', c_int),
    ('f_buf', STRING),
    ('f_bufend', STRING),
    ('f_bufptr', STRING),
    ('f_setbuf', STRING),
    ('f_univ_newline', c_int),
    ('f_newlinetypes', c_int),
    ('f_skipnextlf', c_int),
    ('f_encoding', POINTER(PyObject)),
    ('weakreflist', POINTER(PyObject)),
]
assert sizeof(PyFileObject) == 68, sizeof(PyFileObject)
assert alignment(PyFileObject) == 4, alignment(PyFileObject)
_object._fields_ = [
    ('ob_refcnt', Py_ssize_t),
    ('ob_type', POINTER(_typeobject)),
]
assert sizeof(_object) == 8, sizeof(_object)
assert alignment(_object) == 4, alignment(_object)
class PyVarObject(Structure):
    pass
PyVarObject._fields_ = [
    ('ob_refcnt', Py_ssize_t),
    ('ob_type', POINTER(_typeobject)),
    ('ob_size', Py_ssize_t),
]
assert sizeof(PyVarObject) == 12, sizeof(PyVarObject)
assert alignment(PyVarObject) == 4, alignment(PyVarObject)
unaryfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject))
binaryfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), POINTER(PyObject))
ternaryfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), POINTER(PyObject), POINTER(PyObject))
inquiry = CFUNCTYPE(c_int, POINTER(PyObject))
lenfunc = CFUNCTYPE(Py_ssize_t, POINTER(PyObject))
coercion = CFUNCTYPE(c_int, POINTER(POINTER(PyObject)), POINTER(POINTER(PyObject)))
intargfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), c_int)
intintargfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), c_int, c_int)
ssizeargfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), c_long)
ssizessizeargfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), c_long, c_long)
intobjargproc = CFUNCTYPE(c_int, POINTER(PyObject), c_int, POINTER(PyObject))
intintobjargproc = CFUNCTYPE(c_int, POINTER(PyObject), c_int, c_int, POINTER(PyObject))
ssizeobjargproc = CFUNCTYPE(c_int, POINTER(PyObject), c_long, POINTER(PyObject))
ssizessizeobjargproc = CFUNCTYPE(c_int, POINTER(PyObject), c_long, c_long, POINTER(PyObject))
objobjargproc = CFUNCTYPE(c_int, POINTER(PyObject), POINTER(PyObject), POINTER(PyObject))
getreadbufferproc = CFUNCTYPE(c_int, POINTER(PyObject), c_int, POINTER(c_void_p))
getwritebufferproc = CFUNCTYPE(c_int, POINTER(PyObject), c_int, POINTER(c_void_p))
getsegcountproc = CFUNCTYPE(c_int, POINTER(PyObject), POINTER(c_int))
getcharbufferproc = CFUNCTYPE(c_int, POINTER(PyObject), c_int, POINTER(STRING))
readbufferproc = CFUNCTYPE(Py_ssize_t, POINTER(PyObject), c_long, POINTER(c_void_p))
writebufferproc = CFUNCTYPE(Py_ssize_t, POINTER(PyObject), c_long, POINTER(c_void_p))
segcountproc = CFUNCTYPE(Py_ssize_t, POINTER(PyObject), POINTER(Py_ssize_t))
charbufferproc = CFUNCTYPE(Py_ssize_t, POINTER(PyObject), c_long, POINTER(STRING))
objobjproc = CFUNCTYPE(c_int, POINTER(PyObject), POINTER(PyObject))
visitproc = CFUNCTYPE(c_int, POINTER(PyObject), c_void_p)
traverseproc = CFUNCTYPE(c_int, POINTER(PyObject), CFUNCTYPE(c_int, POINTER(PyObject), c_void_p), c_void_p)
class PyNumberMethods(Structure):
    pass
PyNumberMethods._fields_ = [
    ('nb_add', binaryfunc),
    ('nb_subtract', binaryfunc),
    ('nb_multiply', binaryfunc),
    ('nb_divide', binaryfunc),
    ('nb_remainder', binaryfunc),
    ('nb_divmod', binaryfunc),
    ('nb_power', ternaryfunc),
    ('nb_negative', unaryfunc),
    ('nb_positive', unaryfunc),
    ('nb_absolute', unaryfunc),
    ('nb_nonzero', inquiry),
    ('nb_invert', unaryfunc),
    ('nb_lshift', binaryfunc),
    ('nb_rshift', binaryfunc),
    ('nb_and', binaryfunc),
    ('nb_xor', binaryfunc),
    ('nb_or', binaryfunc),
    ('nb_coerce', coercion),
    ('nb_int', unaryfunc),
    ('nb_long', unaryfunc),
    ('nb_float', unaryfunc),
    ('nb_oct', unaryfunc),
    ('nb_hex', unaryfunc),
    ('nb_inplace_add', binaryfunc),
    ('nb_inplace_subtract', binaryfunc),
    ('nb_inplace_multiply', binaryfunc),
    ('nb_inplace_divide', binaryfunc),
    ('nb_inplace_remainder', binaryfunc),
    ('nb_inplace_power', ternaryfunc),
    ('nb_inplace_lshift', binaryfunc),
    ('nb_inplace_rshift', binaryfunc),
    ('nb_inplace_and', binaryfunc),
    ('nb_inplace_xor', binaryfunc),
    ('nb_inplace_or', binaryfunc),
    ('nb_floor_divide', binaryfunc),
    ('nb_true_divide', binaryfunc),
    ('nb_inplace_floor_divide', binaryfunc),
    ('nb_inplace_true_divide', binaryfunc),
    ('nb_index', lenfunc),
]
assert sizeof(PyNumberMethods) == 156, sizeof(PyNumberMethods)
assert alignment(PyNumberMethods) == 4, alignment(PyNumberMethods)
class PySequenceMethods(Structure):
    pass
PySequenceMethods._fields_ = [
    ('sq_length', lenfunc),
    ('sq_concat', binaryfunc),
    ('sq_repeat', ssizeargfunc),
    ('sq_item', ssizeargfunc),
    ('sq_slice', ssizessizeargfunc),
    ('sq_ass_item', ssizeobjargproc),
    ('sq_ass_slice', ssizessizeobjargproc),
    ('sq_contains', objobjproc),
    ('sq_inplace_concat', binaryfunc),
    ('sq_inplace_repeat', ssizeargfunc),
]
assert sizeof(PySequenceMethods) == 40, sizeof(PySequenceMethods)
assert alignment(PySequenceMethods) == 4, alignment(PySequenceMethods)
class PyMappingMethods(Structure):
    pass
PyMappingMethods._fields_ = [
    ('mp_length', lenfunc),
    ('mp_subscript', binaryfunc),
    ('mp_ass_subscript', objobjargproc),
]
assert sizeof(PyMappingMethods) == 12, sizeof(PyMappingMethods)
assert alignment(PyMappingMethods) == 4, alignment(PyMappingMethods)
class PyBufferProcs(Structure):
    pass
PyBufferProcs._fields_ = [
    ('bf_getreadbuffer', readbufferproc),
    ('bf_getwritebuffer', writebufferproc),
    ('bf_getsegcount', segcountproc),
    ('bf_getcharbuffer', charbufferproc),
]
assert sizeof(PyBufferProcs) == 16, sizeof(PyBufferProcs)
assert alignment(PyBufferProcs) == 4, alignment(PyBufferProcs)
freefunc = CFUNCTYPE(None, c_void_p)
destructor = CFUNCTYPE(None, POINTER(PyObject))
printfunc = CFUNCTYPE(c_int, POINTER(PyObject), POINTER(FILE), c_int)
getattrfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), STRING)
getattrofunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), POINTER(PyObject))
setattrfunc = CFUNCTYPE(c_int, POINTER(PyObject), STRING, POINTER(PyObject))
setattrofunc = CFUNCTYPE(c_int, POINTER(PyObject), POINTER(PyObject), POINTER(PyObject))
cmpfunc = CFUNCTYPE(c_int, POINTER(PyObject), POINTER(PyObject))
reprfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject))
hashfunc = CFUNCTYPE(c_long, POINTER(PyObject))
richcmpfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), POINTER(PyObject), c_int)
getiterfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject))
iternextfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject))
descrgetfunc = CFUNCTYPE(POINTER(PyObject), POINTER(PyObject), POINTER(PyObject), POINTER(PyObject))
descrsetfunc = CFUNCTYPE(c_int, POINTER(PyObject), POINTER(PyObject), POINTER(PyObject))
initproc = CFUNCTYPE(c_int, POINTER(PyObject), POINTER(PyObject), POINTER(PyObject))
newfunc = CFUNCTYPE(POINTER(PyObject), POINTER(_typeobject), POINTER(PyObject), POINTER(PyObject))
allocfunc = CFUNCTYPE(POINTER(PyObject), POINTER(_typeobject), c_long)
class PyMethodDef(Structure):
    pass
PyMethodDef._fields_ = []
PyMethodDef.__name__ = "PyMethodDef_"
class PyMemberDef(Structure):
    pass
PyMemberDef._fields_ = []
PyMemberDef.__name__ = "PyMemberDef_"
class PyGetSetDef(Structure):
    pass
PyGetSetDef._fields_ = []
PyGetSetDef.__name__ = "PyGetSetDef_"
_typeobject._fields_ = [
    ('ob_refcnt', Py_ssize_t),
    ('ob_type', POINTER(_typeobject)),
    ('ob_size', Py_ssize_t),
    ('tp_name', STRING),
    ('tp_basicsize', Py_ssize_t),
    ('tp_itemsize', Py_ssize_t),
    ('tp_dealloc', destructor),
    ('tp_print', printfunc),
    ('tp_getattr', getattrfunc),
    ('tp_setattr', setattrfunc),
    ('tp_compare', cmpfunc),
    ('tp_repr', reprfunc),
    ('tp_as_number', POINTER(PyNumberMethods)),
    ('tp_as_sequence', POINTER(PySequenceMethods)),
    ('tp_as_mapping', POINTER(PyMappingMethods)),
    ('tp_hash', hashfunc),
    ('tp_call', ternaryfunc),
    ('tp_str', reprfunc),
    ('tp_getattro', getattrofunc),
    ('tp_setattro', setattrofunc),
    ('tp_as_buffer', POINTER(PyBufferProcs)),
    ('tp_flags', c_long),
    ('tp_doc', STRING),
    ('tp_traverse', traverseproc),
    ('tp_clear', inquiry),
    ('tp_richcompare', richcmpfunc),
    ('tp_weaklistoffset', Py_ssize_t),
    ('tp_iter', getiterfunc),
    ('tp_iternext', iternextfunc),
    ('tp_methods', POINTER(PyMethodDef)),
    ('tp_members', POINTER(PyMemberDef)),
    ('tp_getset', POINTER(PyGetSetDef)),
    ('tp_base', POINTER(_typeobject)),
    ('tp_dict', POINTER(PyObject)),
    ('tp_descr_get', descrgetfunc),
    ('tp_descr_set', descrsetfunc),
    ('tp_dictoffset', Py_ssize_t),
    ('tp_init', initproc),
    ('tp_alloc', allocfunc),
    ('tp_new', newfunc),
    ('tp_free', freefunc),
    ('tp_is_gc', inquiry),
    ('tp_bases', POINTER(PyObject)),
    ('tp_mro', POINTER(PyObject)),
    ('tp_cache', POINTER(PyObject)),
    ('tp_subclasses', POINTER(PyObject)),
    ('tp_weaklist', POINTER(PyObject)),
    ('tp_del', destructor),
]
_typeobject.__name__ = "_typeobject_"
assert sizeof(_typeobject) == 192, sizeof(_typeobject)
assert alignment(_typeobject) == 4, alignment(_typeobject)
PyTypeObject = _typeobject
class _heaptypeobject(Structure):
    pass
_heaptypeobject._fields_ = [
    ('ht_type', PyTypeObject),
    ('as_number', PyNumberMethods),
    ('as_mapping', PyMappingMethods),
    ('as_sequence', PySequenceMethods),
    ('as_buffer', PyBufferProcs),
    ('ht_name', POINTER(PyObject)),
    ('ht_slots', POINTER(PyObject)),
]
assert sizeof(_heaptypeobject) == 424, sizeof(_heaptypeobject)
assert alignment(_heaptypeobject) == 4, alignment(_heaptypeobject)
PyHeapTypeObject = _heaptypeobject
Py_uintptr_t = c_uint
Py_intptr_t = c_int
__all__ = ['__uint16_t', 'PyMethodDef', 'objobjargproc', '__int16_t',
           'unaryfunc', '__darwin_pthread_condattr_t',
           'readbufferproc', '__darwin_id_t', 'key_t',
           '__darwin_time_t', 'ucontext64_t', '__darwin_nl_item',
           'pthread_once_t', '_opaque_pthread_condattr_t', 'FILE',
           'pthread_mutexattr_t', 'size_t', 'Py_uintptr_t',
           '_FP_ZERO', '_FP_SUPERNORMAL', 'cmpfunc', '__uint32_t',
           'mcontext_t', 'PySequenceMethods', 'uint8_t', 'fpos_t',
           'P_PGID', 'qaddr_t', '__darwin_gid_t', 'blkcnt_t',
           'uint_least16_t', '__darwin_dev_t', 'time_t', '_FP_NORMAL',
           'allocfunc', 'getiterfunc', 'int32_t',
           '__darwin_fsfilcnt_t', 'lenfunc', 'intptr_t',
           'uint_least64_t', 'blksize_t', 'user_addr_t', 'PyObject',
           'int_least32_t', 'sigaltstack', 'Py_intptr_t', 'ostat',
           '__darwin_pthread_t', 'u_char', 'fixpt_t', 'uid_t',
           'u_int64_t', 'u_int16_t', 'register_t',
           '__darwin_ucontext_t', 'cc_t', 'in_port_t', 'ternaryfunc',
           '__darwin_ssize_t', 'descrsetfunc', '__darwin_mcontext_t',
           '__darwin_sigset_t', 'ct_rune_t', 'uint16_t',
           '__darwin_ptrdiff_t', 'float_t', 'int_fast32_t', 'va_list',
           'uint_fast16_t', 'sigset_t', '__int32_t', 'fd_mask',
           'binaryfunc', 'fsfilcnt_t', 'ucontext', 'ssizeobjargproc',
           'uint_fast32_t', 'freefunc', 'tm', '__uint64_t', 'mode_t',
           'timespec', '__darwin_suseconds_t', 'PyNumberMethods',
           '__sigaction', 'sigevent', 'user_ulong_t', 'user_ssize_t',
           'syscall_arg_t', 'reprfunc', 'int16_t', 'getattrofunc',
           'clock_t', 'ssizeargfunc', 'ssizessizeargfunc',
           '__darwin_socklen_t', '__darwin_intptr_t', 'rune_t',
           '__darwin_va_list', 'caddr_t', 'siginfo_t', 'ucontext_t',
           '__sbuf', 'setattrfunc', 'coercion', 'int_least8_t',
           'getsegcountproc', 'N4wait3DOLLAR_4E', 'div_t', 'newfunc',
           'intintobjargproc', 'id_t', '__darwin_blksize_t', 'ldiv_t',
           'int_least16_t', '__darwin_wctrans_t', 'uint_least8_t',
           'u_int32_t', 'pthread_rwlock_t', 'charbufferproc',
           '__darwin_wchar_t', 'sigval', 'PyGetSetDef',
           'intobjargproc', 'P_PID', 'sigaction',
           '__darwin_natural_t', 'sig_t', '__darwin_blkcnt_t',
           'u_int', '_opaque_pthread_cond_t', '__darwin_size_t',
           'ssizessizeobjargproc', 'segsz_t', 'ushort',
           '__darwin_ct_rune_t', 'pthread_t', '__darwin_ino_t',
           'pthread_attr_t', 'fd_set', '__darwin_useconds_t',
           '__darwin_mcontext64_t', 'ino_t', '__darwin_clock_t',
           'uint_fast8_t', '_typeobject', '__darwin_pthread_key_t',
           'getwritebufferproc', 'traverseproc',
           '__darwin_pthread_handler_rec', 'double_t',
           '__darwin_pthread_mutex_t', 'initproc', 'speed_t',
           '_object', '__darwin_ucontext64_t', 'getreadbufferproc',
           'rlim_t', 'hashfunc', '__darwin_fsblkcnt_t',
           '__darwin_rune_t', 'fsblkcnt_t', 'u_quad_t',
           '_opaque_pthread_rwlockattr_t', 'sigvec',
           '_opaque_pthread_mutexattr_t', 'clockinfo',
           '__darwin_pthread_rwlock_t', 'pthread_condattr_t',
           'destructor', 'rlimit', '__darwin_pthread_mutexattr_t',
           'daddr_t', '__darwin_pthread_once_t', 'stack_t',
           '__darwin_mode_t', 'uint_least32_t', 'wait', 'OSBigEndian',
           '__mbstate_t', 'uintptr_t', '__darwin_mach_port_t',
           '__uint8_t', '__darwin_uid_t', 'itimerval', '__int8_t',
           'PyMemberDef', '_opaque_pthread_mutex_t', 'int8_t',
           '__darwin_uuid_t', '_opaque_pthread_attr_t', 'uintmax_t',
           'intargfunc', 'off_t', 'gid_t', 'sigstack', 'filesec_t',
           'mcontext', 'int_least64_t', '_FP_NAN', 'pid_t',
           'visitproc', 'N4wait3DOLLAR_3E', 'quad_t', 'uint_fast64_t',
           'u_long', 'intmax_t', 'sigcontext', 'swblk_t', '__siginfo',
           'winsize', '__darwin_mbstate_t', 'useconds_t',
           'richcmpfunc', 'pthread_key_t', 'uint64_t', 'u_int8_t',
           'writebufferproc', 'pthread_cond_t', '_FP_SUBNORMAL',
           '__darwin_wctype_t', '_opaque_pthread_once_t',
           'OSLittleEndian', 'int_fast16_t', 'int64_t',
           '_FP_INFINITE', 'timezone', '_heaptypeobject', '__sFILE',
           'ucontext64', 'sig_atomic_t', 'u_short', 'nlink_t',
           'PyVarObject', 'mcontext64', 'lldiv_t',
           '__darwin_pthread_rwlockattr_t', 'descrgetfunc',
           'OSUnknownByteOrder', 'timeval', '__darwin_stack_t',
           'inquiry', 'printfunc', 'int_fast64_t', 'int_fast8_t',
           'PyTypeObject', '__sFILEX', 'stat', 'getcharbufferproc',
           'uint32_t', 'intintargfunc', 'PyBufferProcs',
           '__darwin_pthread_attr_t', '__darwin_mach_port_name_t',
           'user_time_t', 'PyFileObject', 'uint', 'termios',
           '__darwin_wint_t', '__darwin_pthread_cond_t', 'objobjproc',
           'user_size_t', 'pthread_rwlockattr_t', 'rusage',
           'PyMappingMethods', 'setattrofunc', 'idtype_t',
           'segcountproc', '__darwin_pid_t', '__sigaction_u',
           '_opaque_pthread_rwlock_t', 'in_addr_t', '__darwin_off_t',
           '_opaque_pthread_t', 'tcflag_t', 'iternextfunc', 'P_ALL',
           'pthread_mutex_t', '__int64_t', 'getattrfunc', 'ssize_t',
           'mcontext64_t', 'user_long_t', 'dev_t', '_filesec',
           'suseconds_t', 'PyHeapTypeObject', 'Py_ssize_t']
