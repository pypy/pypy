import py
import sys

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform
from rpython.conftest import cdir

libdir = py.path.local(cdir).join('src', 'libmpdec')

compile_extra = []
if sys.maxsize > 1<<32:
    compile_extra.append("-DCONFIG_64")
else:
    compile_extra.append("-DCONFIG_32")

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
    compile_extra=compile_extra,
    libraries=['m'],
    )

class CConfig:
    _compilation_info_ = eci

    MPD_IEEE_CONTEXT_MAX_BITS = platform.ConstantInteger(
        'MPD_IEEE_CONTEXT_MAX_BITS')

globals().update(platform.configure(CConfig))
