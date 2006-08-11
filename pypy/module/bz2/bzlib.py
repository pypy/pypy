from ctypes import *
STRING = c_char_p


__darwin_nl_item = c_int
__darwin_wctrans_t = c_int
__darwin_wctype_t = c_ulong
class bz_stream(Structure):
    pass
bz_stream._fields_ = [
    ('next_in', POINTER(c_char)),
    ('avail_in', c_uint),
    ('total_in_lo32', c_uint),
    ('total_in_hi32', c_uint),
    ('next_out', POINTER(c_char)),
    ('avail_out', c_uint),
    ('total_out_lo32', c_uint),
    ('total_out_hi32', c_uint),
    ('state', c_void_p),
    ('bzalloc', CFUNCTYPE(c_void_p, c_void_p, c_int, c_int)),
    ('bzfree', CFUNCTYPE(None, c_void_p, c_void_p)),
    ('opaque', c_void_p),
]
assert sizeof(bz_stream) == 48, sizeof(bz_stream)
assert alignment(bz_stream) == 4, alignment(bz_stream)
BZFILE = None
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
assert sizeof(__sFILE) == 88, sizeof(__sFILE)
assert alignment(__sFILE) == 4, alignment(__sFILE)
FILE = __sFILE
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
__all__ = ['__uint16_t', '__darwin_off_t', '__uint64_t', '__int16_t',
           '__darwin_pthread_condattr_t', '__darwin_pthread_key_t',
           '__darwin_pthread_handler_rec', '__darwin_id_t',
           '__darwin_ucontext64_t', '__darwin_pthread_mutex_t',
           '__darwin_wctype_t', '_opaque_pthread_once_t',
           '__darwin_time_t', '__darwin_nl_item',
           '_opaque_pthread_condattr_t', '__darwin_pthread_rwlock_t',
           'FILE', 'size_t', '__darwin_pthread_rwlockattr_t',
           '__darwin_fsblkcnt_t', '__darwin_rune_t',
           '__darwin_intptr_t', 'ucontext64', '_opaque_pthread_t',
           '__darwin_va_list', '__uint32_t', '__darwin_sigset_t',
           '__sbuf', 'fpos_t', '_opaque_pthread_mutexattr_t',
           '__darwin_socklen_t', '__darwin_suseconds_t',
           '__darwin_gid_t', '__darwin_uuid_t', '__darwin_dev_t',
           '__darwin_pthread_mutexattr_t', '__darwin_stack_t',
           '__darwin_pthread_once_t', '__darwin_ucontext_t',
           '__darwin_blksize_t', '__darwin_mode_t', '__sFILE',
           '__darwin_wctrans_t', '__darwin_fsfilcnt_t', '__mbstate_t',
           '__sFILEX', '_opaque_pthread_rwlockattr_t',
           '__darwin_mach_port_t', '__uint8_t', '__darwin_uid_t',
           '__int8_t', 'sigaltstack', '__darwin_wchar_t',
           '_opaque_pthread_mutex_t', '__darwin_pthread_attr_t',
           '__darwin_mach_port_name_t', 'BZFILE',
           '__darwin_pthread_t', '_opaque_pthread_attr_t', 'ucontext',
           '__darwin_wint_t', '__darwin_pthread_cond_t',
           '__darwin_mcontext64_t', '__darwin_natural_t',
           '_opaque_pthread_cond_t', '__darwin_blkcnt_t', 'mcontext',
           '__darwin_ssize_t', 'mcontext64', '__darwin_mcontext_t',
           '__darwin_size_t', '__darwin_pid_t', '__darwin_ptrdiff_t',
           '_opaque_pthread_rwlock_t', '__darwin_ct_rune_t',
           'va_list', '__darwin_ino_t', '__int32_t', '__int64_t',
           '__darwin_mbstate_t', '__darwin_useconds_t', 'bz_stream',
           '__darwin_clock_t']
