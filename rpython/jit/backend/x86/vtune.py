"""
Support for VTune Amplifier
"""
from rpython.rtyper.tool import rffi_platform
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo


eci = ExternalCompilationInfo(
    post_include_bits=["""
RPY_EXTERN void rpy_vtune_register(char *, long, long);
"""],
    libraries=["dl", "jitprofiling"],
    library_dirs=["/opt/intel/system_studio_2018/vtune_amplifier/lib64/"],
    separate_module_sources=[r"""
#include "/opt/intel/system_studio_2018/vtune_amplifier/include/jitprofiling.h"

RPY_EXTERN void rpy_make_dlopen_strong(char *funcname, Signed addr, Signed size)
{
    // make *really* sure that dlopen&Co are linked so that vtune is happy
    dlopen(NULL, 0);
    dlsym(NULL, NULL);
    dlclose(NULL);
}

RPY_EXTERN void rpy_vtune_register(char *funcname, Signed addr, Signed size)
{
    iJIT_Method_Load_V2 jmethod = {0};

    fprintf(stderr, "call vtune register\n");

    if (iJIT_IsProfilingActive() != iJIT_SAMPLING_ON) {
        return;
    }

    fprintf(stderr, "actually vtune register\n");

    jmethod.method_id = iJIT_GetNewMethodID();
    jmethod.method_name = funcname;
    jmethod.method_load_address = (void *)addr;
    jmethod.method_size = size;
    jmethod.module_name = "rpyjit";

    iJIT_NotifyEvent(iJVM_EVENT_TYPE_METHOD_LOAD_FINISHED_V2,
                     (void*)&jmethod);
}
"""])



try:
    rffi_platform.verify_eci(eci)

    rpy_vtune_register = rffi.llexternal(
        "rpy_vtune_register",
        [rffi.CCHARP, lltype.Signed, lltype.Signed],
        lltype.Void,
        compilation_info=eci,
        _nowrapper=True,
        sandboxsafe=True)

    def register_vtune_symbol(name, start_addr, size):
        with rffi.scoped_str2charp("JIT: " + name) as loopname:
            rpy_vtune_register(loopname, start_addr, size)

except rffi_platform.CompilationError as e:
    print "WARNING: not using VTune integration", e
    def register_vtune_symbol(name, start_addr, size):
        pass

