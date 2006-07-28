from ctypes import *
STRING = c_char_p


OSLittleEndian = 1
OSUnknownByteOrder = 0
OSBigEndian = 2
P_ALL = 0
P_PID = 1
P_PGID = 2
__darwin_nl_item = c_int
__darwin_wctrans_t = c_int
__darwin_wctype_t = c_ulong
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
u_int8_t = c_ubyte
u_int16_t = c_ushort
u_int32_t = c_uint
u_int64_t = c_ulonglong
int32_t = c_int
register_t = int32_t
user_addr_t = u_int64_t
user_size_t = u_int64_t
int64_t = c_longlong
user_ssize_t = int64_t
user_long_t = int64_t
user_ulong_t = u_int64_t
user_time_t = int64_t
syscall_arg_t = u_int64_t

# values for unnamed enumeration
class bio_st(Structure):
    pass
BIO = bio_st
bio_info_cb = CFUNCTYPE(None, POINTER(bio_st), c_int, STRING, c_int, c_long, c_long)
class bio_method_st(Structure):
    pass
bio_method_st._fields_ = [
    ('type', c_int),
    ('name', STRING),
    ('bwrite', CFUNCTYPE(c_int, POINTER(BIO), STRING, c_int)),
    ('bread', CFUNCTYPE(c_int, POINTER(BIO), STRING, c_int)),
    ('bputs', CFUNCTYPE(c_int, POINTER(BIO), STRING)),
    ('bgets', CFUNCTYPE(c_int, POINTER(BIO), STRING, c_int)),
    ('ctrl', CFUNCTYPE(c_long, POINTER(BIO), c_int, c_long, c_void_p)),
    ('create', CFUNCTYPE(c_int, POINTER(BIO))),
    ('destroy', CFUNCTYPE(c_int, POINTER(BIO))),
    ('callback_ctrl', CFUNCTYPE(c_long, POINTER(BIO), c_int, POINTER(bio_info_cb))),
]
assert sizeof(bio_method_st) == 40, sizeof(bio_method_st)
assert alignment(bio_method_st) == 4, alignment(bio_method_st)
BIO_METHOD = bio_method_st
class crypto_ex_data_st(Structure):
    pass
class stack_st(Structure):
    pass
STACK = stack_st
crypto_ex_data_st._fields_ = [
    ('sk', POINTER(STACK)),
    ('dummy', c_int),
]
assert sizeof(crypto_ex_data_st) == 8, sizeof(crypto_ex_data_st)
assert alignment(crypto_ex_data_st) == 4, alignment(crypto_ex_data_st)
CRYPTO_EX_DATA = crypto_ex_data_st
bio_st._fields_ = [
    ('method', POINTER(BIO_METHOD)),
    ('callback', CFUNCTYPE(c_long, POINTER(bio_st), c_int, STRING, c_int, c_long, c_long)),
    ('cb_arg', STRING),
    ('init', c_int),
    ('shutdown', c_int),
    ('flags', c_int),
    ('retry_reason', c_int),
    ('num', c_int),
    ('ptr', c_void_p),
    ('next_bio', POINTER(bio_st)),
    ('prev_bio', POINTER(bio_st)),
    ('references', c_int),
    ('num_read', c_ulong),
    ('num_write', c_ulong),
    ('ex_data', CRYPTO_EX_DATA),
]
assert sizeof(bio_st) == 64, sizeof(bio_st)
assert alignment(bio_st) == 4, alignment(bio_st)
class bio_f_buffer_ctx_struct(Structure):
    pass
bio_f_buffer_ctx_struct._fields_ = [
    ('ibuf_size', c_int),
    ('obuf_size', c_int),
    ('ibuf', STRING),
    ('ibuf_len', c_int),
    ('ibuf_off', c_int),
    ('obuf', STRING),
    ('obuf_len', c_int),
    ('obuf_off', c_int),
]
assert sizeof(bio_f_buffer_ctx_struct) == 32, sizeof(bio_f_buffer_ctx_struct)
assert alignment(bio_f_buffer_ctx_struct) == 4, alignment(bio_f_buffer_ctx_struct)
BIO_F_BUFFER_CTX = bio_f_buffer_ctx_struct
class hostent(Structure):
    pass
class CRYPTO_dynlock_value(Structure):
    pass
class CRYPTO_dynlock(Structure):
    pass
CRYPTO_dynlock._fields_ = [
    ('references', c_int),
    ('data', POINTER(CRYPTO_dynlock_value)),
]
assert sizeof(CRYPTO_dynlock) == 8, sizeof(CRYPTO_dynlock)
assert alignment(CRYPTO_dynlock) == 4, alignment(CRYPTO_dynlock)
BIO_dummy = bio_st
CRYPTO_EX_new = CFUNCTYPE(c_int, c_void_p, c_void_p, POINTER(CRYPTO_EX_DATA), c_int, c_long, c_void_p)
CRYPTO_EX_free = CFUNCTYPE(None, c_void_p, c_void_p, POINTER(CRYPTO_EX_DATA), c_int, c_long, c_void_p)
CRYPTO_EX_dup = CFUNCTYPE(c_int, POINTER(CRYPTO_EX_DATA), POINTER(CRYPTO_EX_DATA), c_void_p, c_int, c_long, c_void_p)
class crypto_ex_data_func_st(Structure):
    pass
crypto_ex_data_func_st._fields_ = [
    ('argl', c_long),
    ('argp', c_void_p),
    ('new_func', POINTER(CRYPTO_EX_new)),
    ('free_func', POINTER(CRYPTO_EX_free)),
    ('dup_func', POINTER(CRYPTO_EX_dup)),
]
assert sizeof(crypto_ex_data_func_st) == 20, sizeof(crypto_ex_data_func_st)
assert alignment(crypto_ex_data_func_st) == 4, alignment(crypto_ex_data_func_st)
CRYPTO_EX_DATA_FUNCS = crypto_ex_data_func_st
class st_CRYPTO_EX_DATA_IMPL(Structure):
    pass
CRYPTO_EX_DATA_IMPL = st_CRYPTO_EX_DATA_IMPL
CRYPTO_MEM_LEAK_CB = CFUNCTYPE(c_void_p, c_ulong, STRING, c_int, c_int, c_void_p)
openssl_fptr = CFUNCTYPE(None)
stack_st._fields_ = [
    ('num', c_int),
    ('data', POINTER(STRING)),
    ('sorted', c_int),
    ('num_alloc', c_int),
    ('comp', CFUNCTYPE(c_int, POINTER(STRING), POINTER(STRING))),
]
assert sizeof(stack_st) == 20, sizeof(stack_st)
assert alignment(stack_st) == 4, alignment(stack_st)
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
assert sizeof(__sbuf) == 8, sizeof(__sbuf)
assert alignment(__sbuf) == 4, alignment(__sbuf)
class __sFILEX(Structure):
    pass
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
__darwin_dev_t = __int32_t
dev_t = __darwin_dev_t
__darwin_mode_t = __uint16_t
mode_t = __darwin_mode_t
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
__darwin_fsblkcnt_t = c_uint
__darwin_fsfilcnt_t = c_uint
__darwin_gid_t = __uint32_t
__darwin_id_t = __uint32_t
__darwin_ino_t = __uint32_t
__darwin_mach_port_name_t = __darwin_natural_t
__darwin_mach_port_t = __darwin_mach_port_name_t
__darwin_mcontext_t = POINTER(mcontext)
__darwin_mcontext64_t = POINTER(mcontext64)
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
pthread_attr_t = __darwin_pthread_attr_t
sigset_t = __darwin_sigset_t
ucontext_t = __darwin_ucontext_t
ucontext64_t = __darwin_ucontext64_t
uid_t = __darwin_uid_t
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

# values for enumeration 'idtype_t'
idtype_t = c_int # enum
id_t = __darwin_id_t
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
__gnuc_va_list = STRING
int8_t = c_byte
int16_t = c_short
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
intptr_t = c_long
uintptr_t = c_ulong
intmax_t = c_longlong
uintmax_t = c_ulonglong
__all__ = ['__uint16_t', '__int16_t', '__darwin_pthread_condattr_t',
           'CRYPTO_dynlock', '__darwin_id_t', 'CRYPTO_EX_DATA_IMPL',
           '__darwin_time_t', 'ucontext64_t', '__darwin_nl_item',
           '_opaque_pthread_condattr_t', 'FILE', 'size_t',
           '__uint32_t', 'mcontext_t', 'uint8_t', 'fpos_t', 'P_PGID',
           '__darwin_gid_t', 'uint_least16_t',
           '__darwin_pthread_handler_rec', 'CRYPTO_EX_free',
           '__darwin_pid_t', 'int_fast8_t', '__darwin_fsfilcnt_t',
           'intptr_t', 'uint_least64_t', 'user_addr_t',
           'int_least32_t', 'sigaltstack', '__darwin_pthread_t',
           'BIO_METHOD', 'uid_t', 'u_int64_t', 'u_int16_t',
           'register_t', '__darwin_ucontext_t',
           'bio_f_buffer_ctx_struct', '__darwin_ssize_t',
           '__darwin_mcontext_t', '__darwin_sigset_t', 'ct_rune_t',
           '__darwin_ptrdiff_t', 'int_fast32_t', 'va_list',
           'uint_fast16_t', 'sigset_t', '__int32_t', 'ucontext',
           'uint_fast32_t', '__uint64_t', 'mode_t',
           '__darwin_suseconds_t', '__sigaction', 'sigevent',
           'user_ulong_t', 'user_ssize_t', 'syscall_arg_t', 'int16_t',
           '__darwin_socklen_t', '__darwin_intptr_t', 'rune_t',
           '__darwin_va_list', 'siginfo_t', 'ucontext_t', '__sbuf',
           'int_least8_t', 'N4wait3DOLLAR_4E', 'div_t', 'id_t',
           '__darwin_blksize_t', 'int_least64_t', 'ldiv_t',
           'int_least16_t', '__darwin_wctrans_t', 'uint_least8_t',
           'u_int32_t', '__darwin_wchar_t', 'sigval',
           '__gnuc_va_list', 'P_PID', 'sigaction',
           '__darwin_natural_t', 'sig_t', '__darwin_blkcnt_t',
           'hostent', '_opaque_pthread_cond_t', '__darwin_size_t',
           '__darwin_ct_rune_t', '__darwin_ino_t', 'pthread_attr_t',
           'CRYPTO_MEM_LEAK_CB', '__darwin_useconds_t',
           '__darwin_mcontext64_t', 'uint16_t', '__darwin_clock_t',
           'uint_fast8_t', 'CRYPTO_dynlock_value',
           '__darwin_pthread_key_t', '__darwin_dev_t', 'int32_t',
           '__darwin_pthread_mutex_t', '__darwin_ucontext64_t',
           'st_CRYPTO_EX_DATA_IMPL', 'rlim_t', '__darwin_fsblkcnt_t',
           '__darwin_rune_t', 'BIO_F_BUFFER_CTX', 'openssl_fptr',
           '_opaque_pthread_rwlockattr_t', 'sigvec',
           '_opaque_pthread_mutexattr_t', '__darwin_pthread_rwlock_t',
           'rlimit', '__darwin_pthread_mutexattr_t',
           '__darwin_pthread_once_t', 'stack_t', '__darwin_mode_t',
           'uint_least32_t', 'wait', 'OSBigEndian', '__mbstate_t',
           'uintptr_t', '__darwin_mach_port_t', 'CRYPTO_EX_DATA',
           '__darwin_uid_t', '__int8_t', '_opaque_pthread_mutex_t',
           'int8_t', '__darwin_uuid_t', '_opaque_pthread_attr_t',
           'uintmax_t', 'sigstack', 'stack_st', 'bio_info_cb',
           'mcontext', 'crypto_ex_data_func_st', 'pid_t',
           'N4wait3DOLLAR_3E', 'uint_fast64_t', 'intmax_t',
           'sigcontext', '__siginfo', '__darwin_mbstate_t',
           'uint64_t', 'u_int8_t', 'crypto_ex_data_st',
           '__darwin_wctype_t', '_opaque_pthread_once_t',
           'OSLittleEndian', 'int64_t', 'int_fast16_t', 'bio_st',
           '__sFILE', 'ucontext64', 'sig_atomic_t', 'BIO',
           '__uint8_t', 'CRYPTO_EX_dup', 'lldiv_t',
           '__darwin_pthread_rwlockattr_t', 'OSUnknownByteOrder',
           'bio_method_st', 'timeval', '__darwin_stack_t',
           'BIO_dummy', 'int_fast64_t', 'STACK', '__sFILEX',
           'CRYPTO_EX_new', '__darwin_pthread_attr_t',
           '__darwin_mach_port_name_t', 'CRYPTO_EX_DATA_FUNCS',
           'user_time_t', '__darwin_wint_t',
           '__darwin_pthread_cond_t', 'user_size_t', 'rusage',
           'idtype_t', 'mcontext64', '__sigaction_u',
           '_opaque_pthread_rwlock_t', '__darwin_off_t',
           '_opaque_pthread_t', 'P_ALL', '__int64_t', 'uint32_t',
           'mcontext64_t', 'user_long_t', 'dev_t']
