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
