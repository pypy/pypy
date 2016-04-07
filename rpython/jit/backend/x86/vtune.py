"""
Support for VTune Amplifier
"""

from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


eci = ExternalCompilationInfo(
    post_include_bits=["""
RPY_EXTERN void rpy_vtune_register(char *, long, long);
"""],
    include_dirs=["/opt/intel/vtune_amplifier_xe/include"],
    separate_module_sources=["""
#include "/opt/intel/vtune_amplifier_xe/sdk/src/ittnotify/jitprofiling.c"

RPY_EXTERN void rpy_vtune_register(char *funcname, Signed addr, Signed length)
{
    iJIT_Method_Load_V2 jmethod = {0};

    if (iJIT_IsProfilingActive() != iJIT_SAMPLING_ON) {
        return;
    }

    jmethod.method_id = iJIT_GetNewMethodID();
    jmethod.method_name = funcname;
    jmethod.method_load_address = (void *)addr;
    jmethod.method_size = length;
    jmethod.module_name = "rpython_jit";

    iJIT_NotifyEvent(iJVM_EVENT_TYPE_METHOD_LOAD_FINISHED_V2,
                     (void*)&jmethod);
}
"""])

rpy_vtune_register = rffi.llexternal(
        "rpy_vtune_register",
        [rffi.CCHARP, lltype.Signed, lltype.Signed],
        lltype.Void,
        compilation_info=eci,
        _nowrapper=True,
        sandboxsafe=True)
