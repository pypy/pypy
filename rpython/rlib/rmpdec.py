import py
import sys

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.translator import cdir
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform

libdir = py.path.local(cdir).join('src', 'libmpdec')

compile_extra = []
if sys.maxsize > 1<<32:
    compile_extra.append("-DCONFIG_64")
    # This suppose a x64 platform with gcc inline assembler.
    compile_extra.append("-DANSI")
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
        "mpd_qset_ssize", "mpd_qset_uint", "mpd_qset_string",
        "mpd_qsset_ssize", "mpd_qget_ssize",
        "mpd_qcopy", "mpd_qncopy", "mpd_setspecial", "mpd_clear_flags",
        "mpd_qimport_u32", "mpd_qexport_u32", "mpd_qexport_u16",
        "mpd_set_sign", "mpd_set_positive", "mpd_sign", "mpd_qfinalize",
        "mpd_class",
        "mpd_getprec", "mpd_getemin",  "mpd_getemax", "mpd_getround", "mpd_getclamp",
        "mpd_qsetprec", "mpd_qsetemin",  "mpd_qsetemax", "mpd_qsetround", "mpd_qsetclamp",
        "mpd_maxcontext",
        "mpd_qnew", "mpd_del",
        "mpd_to_sci", "mpd_to_sci_size",
        "mpd_iszero", "mpd_isnegative", "mpd_issigned",
        "mpd_isfinite", "mpd_isinfinite",
        "mpd_isnormal", "mpd_issubnormal", "mpd_isspecial", "mpd_iscanonical",
        "mpd_isnan", "mpd_issnan", "mpd_isqnan",
        "mpd_qcmp", "mpd_qcompare", "mpd_qcompare_signal",
        "mpd_qmin", "mpd_qmax", "mpd_qmin_mag", "mpd_qmax_mag",
        "mpd_qnext_minus", "mpd_qnext_plus", "mpd_qnext_toward",
        "mpd_qquantize", "mpd_qreduce",
        "mpd_qplus", "mpd_qminus", "mpd_qabs",
        "mpd_qadd", "mpd_qsub", "mpd_qmul", "mpd_qdiv", "mpd_qdivint",
        "mpd_qrem", "mpd_qrem_near", "mpd_qdivmod", "mpd_qpow", "mpd_qpowmod", 
        "mpd_qfma",
        "mpd_qexp", "mpd_qln", "mpd_qlog10", "mpd_qlogb",
        "mpd_qsqrt", "mpd_qinvert",
        "mpd_qand", "mpd_qor", "mpd_qxor",
        "mpd_qcopy_sign", "mpd_qcopy_abs", "mpd_qcopy_negate",
        "mpd_qround_to_int", "mpd_qround_to_intx",
        "mpd_version",
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
    MPD_UINT_T = platform.SimpleType('mpd_uint_t', rffi.INT)

MPD_UINT_T = platform.configure(CConfig)['MPD_UINT_T']
MPD_UINT_PTR = rffi.CArrayPtr(MPD_UINT_T)

class CConfig:
    _compilation_info_ = eci

    MPD_IEEE_CONTEXT_MAX_BITS = platform.ConstantInteger(
        'MPD_IEEE_CONTEXT_MAX_BITS')
    MPD_MAX_PREC = platform.ConstantInteger('MPD_MAX_PREC')
    MPD_MAX_EMAX = platform.ConstantInteger('MPD_MAX_EMAX')
    MPD_MIN_EMIN = platform.ConstantInteger('MPD_MIN_EMIN')
    MPD_MIN_ETINY = platform.ConstantInteger('MPD_MIN_ETINY')
    MPD_MAX_SIGNAL_LIST = platform.ConstantInteger('MPD_MAX_SIGNAL_LIST')
    MPD_SIZE_MAX = platform.ConstantInteger('MPD_SIZE_MAX')
    MPD_SSIZE_MAX = platform.ConstantInteger('MPD_SSIZE_MAX')
    MPD_SSIZE_MIN = platform.ConstantInteger('MPD_SSIZE_MIN')

    # Flags
    MPD_POS = platform.ConstantInteger('MPD_POS')
    MPD_NEG = platform.ConstantInteger('MPD_NEG')
    MPD_NAN = platform.ConstantInteger('MPD_NAN')
    MPD_INF = platform.ConstantInteger('MPD_INF')
    MPD_STATIC = platform.ConstantInteger('MPD_STATIC')
    MPD_STATIC_DATA = platform.ConstantInteger('MPD_STATIC_DATA')

    for name in ROUND_CONSTANTS:
        name = 'MPD_' + name
        locals()[name] = platform.ConstantInteger(name)

    for name in STATUS_FLAGS_CONSTANTS:
        locals()[name] = platform.ConstantInteger(name)

    MPD_T = platform.Struct('mpd_t',
                            [('flags', rffi.UCHAR),
                             ('exp', rffi.SSIZE_T),
                             ('digits', rffi.SSIZE_T),
                             ('len', rffi.SSIZE_T),
                             ('alloc', rffi.SSIZE_T),
                             ('data', MPD_UINT_PTR),
                             ])
    MPD_CONTEXT_T = platform.Struct('mpd_context_t',
                                    [('prec', lltype.Signed),
                                     ('emax', lltype.Signed),
                                     ('emin', lltype.Signed),
                                     ('traps', rffi.UINT),
                                     ('status', rffi.UINT),
                                     ('newtrap', rffi.UINT),
                                     ('round', lltype.Signed),
                                     ('clamp', lltype.Signed),
                                     ('allcr', lltype.Signed),
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
mpd_qset_uint = external(
    'mpd_qset_uint', [MPD_PTR, rffi.UINT, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qset_string = external(
    'mpd_qset_string', [MPD_PTR, rffi.CCHARP, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qsset_ssize = external(
    'mpd_qsset_ssize', [MPD_PTR, rffi.SSIZE_T, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qget_ssize = external(
    'mpd_qget_ssize', [MPD_PTR, rffi.UINTP], rffi.SSIZE_T)
mpd_qimport_u32 = external(
    'mpd_qimport_u32', [
        MPD_PTR, rffi.UINTP, rffi.SIZE_T,
        rffi.UCHAR, rffi.UINT, MPD_CONTEXT_PTR, rffi.UINTP], rffi.SIZE_T)
mpd_qexport_u32 = external(
    'mpd_qexport_u32', [
        rffi.CArrayPtr(rffi.UINTP), rffi.SIZE_T, rffi.UINT,
        MPD_PTR, rffi.UINTP], rffi.SIZE_T)
mpd_qexport_u16 = external(
    'mpd_qexport_u16', [
        rffi.CArrayPtr(rffi.USHORTP), rffi.SIZE_T, rffi.UINT,
        MPD_PTR, rffi.UINTP], rffi.SIZE_T)
mpd_qcopy = external(
    'mpd_qcopy', [MPD_PTR, MPD_PTR, rffi.UINTP], rffi.INT)
mpd_qncopy = external(
    'mpd_qncopy', [MPD_PTR], MPD_PTR)
mpd_setspecial = external(
    'mpd_setspecial', [MPD_PTR, rffi.UCHAR, rffi.UCHAR], lltype.Void)
mpd_set_sign = external(
    'mpd_set_sign', [MPD_PTR, rffi.UCHAR], lltype.Void)
mpd_set_positive = external(
    'mpd_set_positive', [MPD_PTR], lltype.Void)
mpd_clear_flags = external(
    'mpd_clear_flags', [MPD_PTR], lltype.Void)
mpd_sign = external(
    'mpd_sign', [MPD_PTR], rffi.UCHAR)
mpd_qfinalize = external(
    'mpd_qfinalize', [MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_class = external(
    'mpd_class', [MPD_PTR, MPD_CONTEXT_PTR], rffi.CCHARP)

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

mpd_qnew = external(
    'mpd_qnew', [], MPD_PTR)
mpd_del = external(
    'mpd_del', [MPD_PTR], lltype.Void)
mpd_free = external(
    'mpd_free', [rffi.VOIDP], lltype.Void, macro=True)

mpd_seterror = external(
    'mpd_seterror', [MPD_PTR, rffi.UINT, rffi.UINTP], lltype.Void)

# Conversion
mpd_to_sci = external(
    'mpd_to_sci', [MPD_PTR, rffi.INT], rffi.CCHARP)
mpd_to_sci_size = external(
    'mpd_to_sci_size', [rffi.CCHARPP, MPD_PTR, rffi.INT], rffi.SSIZE_T)

# Operations
mpd_iszero = external(
    'mpd_iszero', [MPD_PTR], rffi.INT)
mpd_isnegative = external(
    'mpd_isnegative', [MPD_PTR], rffi.INT)
mpd_issigned = external(
    'mpd_issigned', [MPD_PTR], rffi.INT)
mpd_isfinite = external(
    'mpd_isfinite', [MPD_PTR], rffi.INT)
mpd_isinfinite = external(
    'mpd_isinfinite', [MPD_PTR], rffi.INT)
mpd_isnormal = external(
    'mpd_isnormal', [MPD_PTR, MPD_CONTEXT_PTR], rffi.INT)
mpd_issubnormal = external(
    'mpd_issubnormal', [MPD_PTR, MPD_CONTEXT_PTR], rffi.INT)
mpd_isspecial = external(
    'mpd_isspecial', [MPD_PTR], rffi.INT)
mpd_iscanonical = external(
    'mpd_iscanonical', [MPD_PTR], rffi.INT)
mpd_isnan = external(
    'mpd_isnan', [MPD_PTR], rffi.INT)
mpd_issnan = external(
    'mpd_issnan', [MPD_PTR], rffi.INT)
mpd_isqnan = external(
    'mpd_isqnan', [MPD_PTR], rffi.INT)
mpd_qcmp = external(
    'mpd_qcmp', [MPD_PTR, MPD_PTR, rffi.UINTP], rffi.INT)
mpd_qcompare = external(
    'mpd_qcompare',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qcompare_signal = external(
    'mpd_qcompare_signal',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)

mpd_qmin = external(
    'mpd_qmin',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qmax = external(
    'mpd_qmax',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qmin_mag = external(
    'mpd_qmin_mag',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qmax_mag = external(
    'mpd_qmax_mag',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qnext_minus = external(
    'mpd_qnext_minus',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qnext_plus = external(
    'mpd_qnext_plus',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qnext_toward = external(
    'mpd_qnext_toward',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qquantize = external(
    'mpd_qquantize',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qreduce = external(
    'mpd_qreduce',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)

mpd_qplus = external(
    'mpd_qplus',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)
mpd_qminus = external(
    'mpd_qminus',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)
mpd_qabs = external(
    'mpd_qabs',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)
mpd_qadd = external(
    'mpd_qadd',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)
mpd_qsub = external(
    'mpd_qsub',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qmul = external(
    'mpd_qmul',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qdiv = external(
    'mpd_qdiv',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qdivint = external(
    'mpd_qdivint',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qrem = external(
    'mpd_qrem',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qrem_near = external(
    'mpd_qrem_near',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qand = external(
    'mpd_qand',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qor = external(
    'mpd_qor',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qxor = external(
    'mpd_qxor',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qdivmod = external(
    'mpd_qdivmod',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)
mpd_qpow = external(
    'mpd_qpow',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qpowmod = external(
    'mpd_qpowmod',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)
mpd_qfma = external(
    'mpd_qfma',
    [MPD_PTR, MPD_PTR, MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)

mpd_qexp = external(
    'mpd_qexp',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qln = external(
    'mpd_qln',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qlog10 = external(
    'mpd_qlog10',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qlogb = external(
    'mpd_qlogb',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qsqrt = external(
    'mpd_qsqrt',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)
mpd_qinvert = external(
    'mpd_qinvert',
    [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP], lltype.Void)

mpd_qcopy_sign = external(
    'mpd_qcopy_sign',
    [MPD_PTR, MPD_PTR, MPD_PTR, rffi.UINTP],
    lltype.Void)
mpd_qcopy_abs = external(
    'mpd_qcopy_abs',
    [MPD_PTR, MPD_PTR, rffi.UINTP],
    lltype.Void)
mpd_qcopy_negate = external(
    'mpd_qcopy_negate',
    [MPD_PTR, MPD_PTR, rffi.UINTP],
    lltype.Void)

mpd_qround_to_int = external(
    'mpd_qround_to_int', [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)
mpd_qround_to_intx = external(
    'mpd_qround_to_intx', [MPD_PTR, MPD_PTR, MPD_CONTEXT_PTR, rffi.UINTP],
    lltype.Void)

mpd_version = external('mpd_version', [], rffi.CCHARP, macro=True)
