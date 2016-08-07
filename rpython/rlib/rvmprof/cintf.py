import platform as host_platform
import py
import sys
from rpython.tool.udir import udir
from rpython.tool.version import rpythonroot
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rlib import rthread, jit
from rpython.rlib.objectmodel import we_are_translated

class VMProfPlatformUnsupported(Exception):
    pass

ROOT = py.path.local(rpythonroot).join('rpython', 'rlib', 'rvmprof')
SRC = ROOT.join('src')

if sys.platform.startswith('linux'):
    _libs = ['dl']
else:
    _libs = []
eci_kwds = dict(
    include_dirs = [SRC],
    includes = ['rvmprof.h', 'vmprof_stack.h'],
    libraries = _libs,
    separate_module_files = [SRC.join('rvmprof.c')],
    post_include_bits=['#define RPYTHON_VMPROF\n'],
    )
global_eci = ExternalCompilationInfo(**eci_kwds)


def setup():
    if host_platform.machine() == 's390x':
        raise VMProfPlatformUnsupported("rvmprof not supported on"
                                        " s390x CPUs for now")
    compile_extra = ['-DRPYTHON_LL2CTYPES']
    platform.verify_eci(ExternalCompilationInfo(
        compile_extra=compile_extra,
        **eci_kwds))

    eci = global_eci
    vmprof_init = rffi.llexternal("vmprof_init",
                                  [rffi.INT, rffi.DOUBLE, rffi.CCHARP],
                                  rffi.CCHARP, compilation_info=eci)
    vmprof_enable = rffi.llexternal("vmprof_enable", [], rffi.INT,
                                    compilation_info=eci,
                                    save_err=rffi.RFFI_SAVE_ERRNO)
    vmprof_disable = rffi.llexternal("vmprof_disable", [], rffi.INT,
                                     compilation_info=eci,
                                     save_err=rffi.RFFI_SAVE_ERRNO)
    vmprof_register_virtual_function = rffi.llexternal(
                                           "vmprof_register_virtual_function",
                                           [rffi.CCHARP, rffi.LONG, rffi.INT],
                                           rffi.INT, compilation_info=eci)
    vmprof_ignore_signals = rffi.llexternal("vmprof_ignore_signals",
                                            [rffi.INT], lltype.Void,
                                            compilation_info=eci,
                                            _nowrapper=True)

    return CInterface(locals())


class CInterface(object):
    def __init__(self, namespace):
        for k, v in namespace.iteritems():
            setattr(self, k, v)

    def _freeze_(self):
        return True


# --- copy a few declarations from src/vmprof_stack.h ---

VMPROF_CODE_TAG = 1

VMPROFSTACK = lltype.ForwardReference()
PVMPROFSTACK = lltype.Ptr(VMPROFSTACK)
VMPROFSTACK.become(rffi.CStruct("vmprof_stack_s",
                                ('next', PVMPROFSTACK),
                                ('value', lltype.Signed),
                                ('kind', lltype.Signed)))
# ----------


vmprof_tl_stack = rthread.ThreadLocalField(PVMPROFSTACK, "vmprof_tl_stack")
do_use_eci = rffi.llexternal_use_eci(
    ExternalCompilationInfo(includes=['vmprof_stack.h'],
                            include_dirs = [SRC]))

def enter_code(unique_id):
    do_use_eci()
    s = lltype.malloc(VMPROFSTACK, flavor='raw')
    s.c_next = vmprof_tl_stack.get_or_make_raw()
    s.c_value = unique_id
    s.c_kind = VMPROF_CODE_TAG
    vmprof_tl_stack.setraw(s)
    return s

def leave_code(s):
    if not we_are_translated():
        assert vmprof_tl_stack.getraw() == s
    vmprof_tl_stack.setraw(s.c_next)
    lltype.free(s, flavor='raw')

#
# JIT notes:
#
# - When running JIT-generated assembler code, we have different custom
#   code to build the VMPROFSTACK, so the functions above are not used.
#   (It uses kind == VMPROF_JITTED_TAG and the VMPROFSTACK is allocated
#   in the C stack.)
#
# - The jitcode for decorated_jitted_function() in rvmprof.py is
#   special-cased by jtransform.py to produce this:
#
#        rvmprof_code(0, unique_id)
#        res = inline_call FUNC         <- for func(*args)
#        rvmprof_code(1, unique_id)
#        return res
#
#   There is no 'catch_exception', but the second 'rvmprof_code' is
#   meant to be executed even in case there was an exception.  This is
#   done by a special case in pyjitpl.py and blackhole.py.  The point
#   is that the above simple pattern can be detected by the blackhole
#   interp, when it first rebuilds all the intermediate RPython
#   frames; at that point it needs to call jit_enter_code() on all
#   intermediate RPython frames, so it does pattern matching to
#   recognize when it must call that and with which 'unique_id' value.
#
# - The jitcode opcode 'rvmprof_code' doesn't produce any resop.  When
#   meta-interpreting, it causes pyjitpl to call jit_enter_code() or
#   jit_leave_code().  As mentioned above, there is logic to call
#   jit_leave_code() even if we exit with an exception, even though
#   there is no 'catch_exception'.  There is similar logic inside
#   the blackhole interpreter.


def jit_enter_code(unique_id):
    enter_code(unique_id)    # ignore the return value

def jit_leave_code(unique_id):
    s = vmprof_tl_stack.getraw()
    assert s.c_value == unique_id
    leave_code(s)
