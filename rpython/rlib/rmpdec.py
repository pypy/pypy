import py
import sys

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.conftest import cdir

libdir = py.path.local(cdir).join('src', 'libmpdec')

compile_extra = []
if sys.maxsize > 1<<32:
    compile_extra.append("-DCONFIG_64")
    # This suppose a x64 platform with gcc inline assembler.
    compile_extra.append("-DASM")
else:
    compile_extra.append("-DCONFIG_32")
    compile_extra.append("-DANSI")

eci = ExternalCompilationInfo(
    includes=['src/libmpdec/mpdecimal.h'],
    include_dirs=[cdir],
    separate_module_files=[libdir.join('mpdecimal.c'),
                           libdir.join('basearith.c'),
                           libdir.join('convolute.c'),
                           libdir.join('constants.c'),
                           libdir.join('context.c'),
                           libdir.join('io.c'),
                           libdir.join('fourstep.c'),
                           libdir.join('sixstep.c'),
                           libdir.join('transpose.c'),
                           libdir.join('difradix2.c'),
                           libdir.join('numbertheory.c'),
                           libdir.join('fnt.c'),
                           libdir.join('crt.c'),
                           libdir.join('memory.c'),
                           ],
    export_symbols=[
        "mpd_qset_ssize", "mpd_qset_string",
        "mpd_getprec", "mpd_getemin",  "mpd_getemax", "mpd_getround", "mpd_getclamp",
        "mpd_qsetprec", "mpd_qsetemin",  "mpd_qsetemax", "mpd_qsetround", "mpd_qsetclamp",
        "mpd_maxcontext",
        "mpd_to_sci_size",
        "mpd_qcmp",
        ],
    compile_extra=compile_extra,
    libraries=['m'],
    )


ROUND_CONSTANTS = (
    'ROUND_UP', 'ROUND_DOWN', 'ROUND_CEILING', 'ROUND_FLOOR',
    'ROUND_HALF_UP', 'ROUND_HALF_DOWN', 'ROUND_HALF_EVEN',
    'ROUND_05UP', 'ROUND_TRUNC')

STATUS_FLAGS_CONSTANTS = (
    'MPD_Clamped',  'MPD_Conversion_syntax', 'MPD_Division_by_zero', 
    'MPD_Division_impossible', 'MPD_Division_undefined', 'MPD_Fpu_error',
    'MPD_Inexact', 'MPD_Invalid_context', 'MPD_Invalid_operation', 
    'MPD_Malloc_error', 'MPD_Not_implemented', 'MPD_Overflow', 
    'MPD_Rounded', 'MPD_Subnormal', 'MPD_Underflow', 'MPD_Max_status',
    'MPD_IEEE_Invalid_operation', 'MPD_Errors')

class CConfig:
    _compilation_info_ = eci

    MPD_IEEE_CONTEXT_MAX_BITS = platform.ConstantInteger(
        'MPD_IEEE_CONTEXT_MAX_BITS')
    MPD_MAX_PREC = platform.ConstantInteger('MPD_MAX_PREC')

    # Flags
    MPD_POS = platform.ConstantInteger('MPD_POS')
    MPD_NEG = platform.ConstantInteger('MPD_NEG')
    MPD_STATIC = platform.ConstantInteger('MPD_STATIC')
    MPD_STATIC_DATA = platform.ConstantInteger('MPD_STATIC_DATA')

    for name in ROUND_CONSTANTS:
        name = 'MPD_' + name
        locals()[name] = platform.ConstantInteger(name)

    for name in STATUS_FLAGS_CONSTANTS:
        locals()[name] = platform.ConstantInteger(name)

    MPD_T = platform.Struct('mpd_t',
                            [('flags', rffi.UINT),
                             ('exp', rffi.SSIZE_T),
                             ('digits', rffi.SSIZE_T),
                             ('len', rffi.SSIZE_T),
                             ('alloc', rffi.SSIZE_T),
                             ('data', rffi.UINTP),
                             ])
    MPD_CONTEXT_T = platform.Struct('mpd_context_t',
                                    [('traps', rffi.UINT),
                                     ('status', rffi.UINT),
                                     ])


globals().update(platform.configure(CConfig))

MPD_Float_operation = MPD_Not_implemented

def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci, **kwds)

MPD_PTR = lltype.Ptr(MPD_T)
MPD_CONTEXT_PTR = lltype.Ptr(MPD_CONTEXT_T)

# Initialization
mpd_qset_ssize = external(
    'mpd_qset_ssize', [MPD_PTR, rffi.SSIZE_T, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qset_string = external(
    'mpd_qset_string', [MPD_PTR, rffi.CCHARP, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qimport_u32 = external(
    'mpd_qimport_u32', [MPD_PTR, rffi.UINTP, rffi.SIZE_T,
                        rffi.UCHAR, rffi.UINT, MPD_CONTEXT_PTR, rffi.UINTP], rffi.SIZE_T)

# Context operations
mpd_getprec = external(
    'mpd_getprec', [MPD_CONTEXT_PTR], rffi.SSIZE_T)
mpd_getemin = external(
    'mpd_getemin', [MPD_CONTEXT_PTR], rffi.SSIZE_T)
mpd_getemax = external(
    'mpd_getemax', [MPD_CONTEXT_PTR], rffi.SSIZE_T)
mpd_getround = external(
    'mpd_getround', [MPD_CONTEXT_PTR], rffi.INT)
mpd_getclamp = external(
    'mpd_getclamp', [MPD_CONTEXT_PTR], rffi.INT)

mpd_qsetprec = external(
    'mpd_qsetprec', [MPD_CONTEXT_PTR, rffi.SSIZE_T], rffi.INT)
mpd_qsetemin = external(
    'mpd_qsetemin', [MPD_CONTEXT_PTR, rffi.SSIZE_T], rffi.INT)
mpd_qsetemax = external(
    'mpd_qsetemax', [MPD_CONTEXT_PTR, rffi.SSIZE_T], rffi.INT)
mpd_qsetround = external(
    'mpd_qsetround', [MPD_CONTEXT_PTR, rffi.INT], rffi.INT)
mpd_qsetclamp = external(
    'mpd_qsetclamp', [MPD_CONTEXT_PTR, rffi.INT], rffi.INT)

mpd_maxcontext = external(
    'mpd_maxcontext', [MPD_CONTEXT_PTR], lltype.Void)

mpd_free = external(
    'mpd_free', [rffi.VOIDP], lltype.Void, macro=True)

mpd_seterror = external(
    'mpd_seterror', [MPD_PTR, rffi.UINT, rffi.UINTP], lltype.Void)

# Conversion
mpd_to_sci_size = external(
    'mpd_to_sci_size', [rffi.CCHARPP, MPD_PTR, rffi.INT], rffi.SSIZE_T)

# Operations
mpd_qcmp = external(
    'mpd_qcmp', [MPD_PTR, MPD_PTR, rffi.UINTP], rffi.INT)
