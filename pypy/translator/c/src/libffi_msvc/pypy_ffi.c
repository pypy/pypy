/* This file contains definition from symbols not defined
 * in the libffi_msvc directory of CPython.
 * most definitions wer copied from the ctypes.c file.
 */

#include "ffi.h"
#include <stdio.h>
#include <stdlib.h>

typedef struct { char c; long long x; } s_long_long;
typedef struct { char c; float x; } s_float;
typedef struct { char c; double x; } s_double;
typedef struct { char c; long double x; } s_long_double;
typedef struct { char c; void *x; } s_void_p;
#define FLOAT_ALIGN (sizeof(s_float) - sizeof(float))
#define DOUBLE_ALIGN (sizeof(s_double) - sizeof(double))
#define LONG_LONG_ALIGN (sizeof(s_long_long) - sizeof(long long))
#define VOID_P_ALIGN (sizeof(s_void_p) - sizeof(void*))
#define LONGDOUBLE_ALIGN (sizeof(s_long_double) - sizeof(long double))

/* align and size are bogus for void, but they must not be zero */
ffi_type ffi_type_void = { 1, 1, FFI_TYPE_VOID };

ffi_type ffi_type_uint8 = { 1, 1, FFI_TYPE_UINT8 };
ffi_type ffi_type_sint8 = { 1, 1, FFI_TYPE_SINT8 };

ffi_type ffi_type_uint16 = { 2, 2, FFI_TYPE_UINT16 };
ffi_type ffi_type_sint16 = { 2, 2, FFI_TYPE_SINT16 };

ffi_type ffi_type_uint32 = { 4, 4, FFI_TYPE_UINT32 };
ffi_type ffi_type_sint32 = { 4, 4, FFI_TYPE_SINT32 };

ffi_type ffi_type_uint64 = { 8, LONG_LONG_ALIGN, FFI_TYPE_UINT64 };
ffi_type ffi_type_sint64 = { 8, LONG_LONG_ALIGN, FFI_TYPE_SINT64 };

ffi_type ffi_type_float = { sizeof(float), FLOAT_ALIGN, FFI_TYPE_FLOAT };
ffi_type ffi_type_double = { sizeof(double), DOUBLE_ALIGN, FFI_TYPE_DOUBLE };
ffi_type ffi_type_longdouble = { sizeof(long double), LONGDOUBLE_ALIGN, FFI_TYPE_LONGDOUBLE };

ffi_type ffi_type_pointer = { sizeof(void *), VOID_P_ALIGN, FFI_TYPE_POINTER };

void ffi_fatalerror(const char* msg) {
  fprintf(stderr, "%s\\n", msg);
  abort();
}
        
