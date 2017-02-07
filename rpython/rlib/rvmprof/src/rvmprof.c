#define _GNU_SOURCE 1

#ifdef RPYTHON_LL2CTYPES
   /* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */

#else
#  include "common_header.h"
#  include "structdef.h"
#  include "src/threadlocal.h"
#  include "rvmprof.h"
#endif

#ifdef VMPROF_UNIX
#include "shared/vmprof_main.h"
#else
#include "shared/vmprof_main_win32.h"
#endif

#ifdef VMPROF_UNIX
#ifdef __clang__
__attribute__((disable_tail_calls))
#elif defined(__GNUC__)
__attribute__((optimize("O1")))
#endif
PY_EVAL_RETURN_T * vmprof_eval(PY_STACK_FRAME_T *f, int throwflag)
{
#ifdef X86_64
    register PY_STACK_FRAME_T * callee_saved asm("rbx");
#elif defined(X86_32)
    register PY_STACK_FRAME_T * callee_saved asm("edi");
#else
#    error "platform not supported"
#endif

    asm volatile(
#ifdef X86_64
        "movq %1, %0\t\n"
#elif defined(X86_32)
        "mov %1, %0\t\n"
#else
#    error "platform not supported"
#endif
        : "=r" (callee_saved)
        : "r" (f) );
    return NULL; // TODO _default_eval_loop(f, throwflag);
}
#endif

void dump_native_symbols(int fileno)
{
// TODO    PyObject * mod = NULL;
// TODO
// TODO    mod = PyImport_ImportModuleNoBlock("vmprof");
// TODO    if (mod == NULL)
// TODO        goto error;
// TODO
// TODO    PyObject_CallMethod(mod, "dump_native_symbols", "(l)", fileno);
// TODO
// TODOerror:
// TODO    Py_XDECREF(mod);
}
