/* allocation functions */
#include "common_header.h"
#ifdef PYPY_STANDALONE
#include <stdlib.h>
#include <src/allocator.h>

#ifndef PYPY_NO_OBMALLOC
# if defined(PYPY_USE_TRIVIAL_MALLOC)
  void *PyObject_Malloc(size_t n) { return malloc(n); }
  void *PyObject_Realloc(void *p, size_t n) { return realloc(p, n); }
  void PyObject_Free(void *p) { if (p) { *((int*)p) = 0xDDDDDDDD; } free(p); }

# elif defined(PYPY_USE_LINUXMEMCHK)
#  include "linuxmemchk.c"

# else
#  ifndef WITH_PYMALLOC
#    define WITH_PYMALLOC
#  endif
/* The same obmalloc as CPython */
#  include "src/obmalloc.c"

# endif
#endif

#endif  /* PYPY_STANDALONE */
