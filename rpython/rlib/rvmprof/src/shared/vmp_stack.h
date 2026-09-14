#pragma once

#include "vmprof.h"

#ifndef RPYTHON_VMPROF
  #if PY_VERSION_HEX >= 0x030b00f0 /* >= 3.11 */
  #define Py_BUILD_CORE
  #if PY_VERSION_HEX >= 0x030E0000 /* >= 3.14 */
  #include "internal/pycore_interpframe.h"
  #else
  #include "internal/pycore_frame.h"
  #endif
  #undef Py_BUILD_CORE
  #include "populate_frames.h"
  #endif
#endif

/* The frame type the profiler walks: the interpreter frame on CPython 3.11
   and later, the frame object on older CPython, the vmprof shadow stack
   entry on PyPy. */
#if PY_VERSION_HEX >= 0x030B0000 && !defined(RPYTHON_VMPROF) /* >= 3.11 */
typedef _PyInterpreterFrame VMP_PY_FRAME_T;
#else
typedef PY_STACK_FRAME_T VMP_PY_FRAME_T;
#endif

int vmp_walk_and_record_stack(VMP_PY_FRAME_T * frame, void **data,
                              int max_depth, int signal, intptr_t pc);

int vmp_native_enabled(void);
int vmp_native_enable(void);
int vmp_ignore_ip(intptr_t ip);
int vmp_binary_search_ranges(intptr_t ip, intptr_t * l, int count);
int vmp_native_symbols_read(void);
void vmp_profile_lines(int);
int vmp_profiles_python_lines(void);

int vmp_ignore_symbol_count(void);
intptr_t * vmp_ignore_symbols(void);
void vmp_set_ignore_symbols(intptr_t * symbols, int count);
void vmp_native_disable(void);

#ifdef __unix__
int vmp_read_vmaps(const char * fname);
#endif
