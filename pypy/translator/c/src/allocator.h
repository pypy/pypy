
/* allocation functions prototypes */
void *PyObject_Malloc(size_t n);
void *PyObject_Realloc(void *p, size_t n);
void PyObject_Free(void *p);


#ifndef PYPY_NOT_MAIN_FILE

#if defined(TRIVIAL_MALLOC_DEBUG)
  void *PyObject_Malloc(size_t n) { return malloc(n); }
  void *PyObject_Realloc(void *p, size_t n) { return realloc(p, n); }
  void PyObject_Free(void *p) { if (p) { *((int*)p) = 0xDDDDDDDD; } free(p); }

#elif defined(LINUXMEMCHK)
#  include "linuxmemchk.c"

#elif defined(NO_OBMALLOC)
  void *PyObject_Malloc(size_t n) { return malloc(n); }
  void *PyObject_Realloc(void *p, size_t n) { return realloc(p, n); }
  void PyObject_Free(void *p) { free(p); }

#else
#  ifndef WITH_PYMALLOC
#    define WITH_PYMALLOC
#  endif
#  include "obmalloc.c"

#endif

#endif
