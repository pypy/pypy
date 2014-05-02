import py
import sys

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi
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
        "mpd_getprec", "mpd_getemin",  "mpd_getemax", "mpd_getround",
        "mpd_getclamp",
        "mpd_qsetprec", "mpd_qsetemin",  "mpd_qsetemax", "mpd_qsetround",
        "mpd_qsetclamp",
        ],
    compile_extra=compile_extra,
    libraries=['m'],
    )


ROUND_CONSTANTS = (
    'ROUND_UP', 'ROUND_DOWN', 'ROUND_CEILING', 'ROUND_FLOOR',
    'ROUND_HALF_UP', 'ROUND_HALF_DOWN', 'ROUND_HALF_EVEN',
    'ROUND_05UP', 'ROUND_TRUNC')

class CConfig:
    _compilation_info_ = eci

    MPD_IEEE_CONTEXT_MAX_BITS = platform.ConstantInteger(
        'MPD_IEEE_CONTEXT_MAX_BITS')
    MPD_MAX_PREC = platform.ConstantInteger('MPD_MAX_PREC')

    for name in ROUND_CONSTANTS:
        name = 'MPD_' + name
        locals()[name] = platform.ConstantInteger(name)

    MPD_CONTEXT_T = platform.Struct('mpd_context_t',
                                    [])

globals().update(platform.configure(CConfig))


def external(name, args, result, **kwds):
    return rffi.llexternal(name, args, result, compilation_info=eci, **kwds)

MPD_CONTEXT_PTR = rffi.CArrayPtr(MPD_CONTEXT_T)

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

