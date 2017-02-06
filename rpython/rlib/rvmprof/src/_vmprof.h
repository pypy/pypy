#pragma once

#include <Python.h>
#include <frameobject.h>

#ifdef VMPROF_WINDOWS
#include "msiinttypes/inttypes.h"
#include "msiinttypes/stdint.h"
#else
#include <inttypes.h>
#include <stdint.h>
#endif

/**
 * This whole setup is very strange. There was just one C file called
 * _vmprof.c which included all *.h files to copy code. Unsure what
 * the goal was with this design, but I assume it just 'GREW'
 *
 * Thus I'm (plan_rich) slowly trying to separate this. *.h files
 * should not have complex implementations (all of them currently have them)
 */


#define SINGLE_BUF_SIZE (8192 - 2 * sizeof(unsigned int))

#define ROUTINE_IS_PYTHON(RIP) ((unsigned long long)RIP & 0x1) == 0
#define ROUTINE_IS_C(RIP) ((unsigned long long)RIP & 0x1) == 1

typedef uint64_t ptr_t;

/* This returns the address of the code object
   as the identifier.  The mapping from identifiers to string
   representations of the code object is done elsewhere, namely:

   * If the code object dies while vmprof is enabled,
     PyCode_Type.tp_dealloc will emit it.  (We don't handle nicely
     for now the case where several code objects are created and die
     at the same memory address.)

   * When _vmprof.disable() is called, then we look around the
     process for code objects and emit all the ones that we can
     find (which we hope is very close to 100% of them).
*/
#define CODE_ADDR_TO_UID(co)  (((intptr_t)(co)))

#define CPYTHON_HAS_FRAME_EVALUATION PY_VERSION_HEX >= 0x30600B0

PyObject* vmprof_eval(PyFrameObject *f, int throwflag);

#ifdef VMPROF_UNIX
#define VMP_SUPPORTS_NATIVE_PROFILING
#endif

#define MARKER_STACKTRACE '\x01'
#define MARKER_VIRTUAL_IP '\x02'
#define MARKER_TRAILER '\x03'
#define MARKER_INTERP_NAME '\x04'   /* deprecated */
#define MARKER_HEADER '\x05'
#define MARKER_TIME_N_ZONE '\x06'
#define MARKER_META '\x07'
#define MARKER_NATIVE_SYMBOLS '\x08'

#define VERSION_BASE '\x00'
#define VERSION_THREAD_ID '\x01'
#define VERSION_TAG '\x02'
#define VERSION_MEMORY '\x03'
#define VERSION_MODE_AWARE '\x04'
#define VERSION_DURATION '\x05'
#define VERSION_TIMESTAMP '\x06'

#define PROFILE_MEMORY '\x01'
#define PROFILE_LINES  '\x02'
#define PROFILE_NATIVE '\x04'

int vmp_write_all(const char *buf, size_t bufsize);
