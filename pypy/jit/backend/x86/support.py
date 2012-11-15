import sys
from pypy.rpython.lltypesystem import lltype, rffi, llmemory
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.jit.backend.x86.arch import WORD

# ____________________________________________________________

memcpy_fn = rffi.llexternal('memcpy', [llmemory.Address, llmemory.Address,
                                       rffi.SIZE_T], lltype.Void,
                            sandboxsafe=True, _nowrapper=True)

# ____________________________________________________________

if WORD == 4:
    extra = ['-DPYPY_X86_CHECK_SSE2']
else:
    extra = []

if sys.platform != 'win32':
    extra = ['-msse2', '-mfpmath=sse',
             '-DPYPY_CPU_HAS_STANDARD_PRECISION'] + extra

ensure_sse2_floats = rffi.llexternal_use_eci(ExternalCompilationInfo(
    compile_extra = extra,
))
