#if defined(RPY_STM) && defined(RPY_STM_ASSERT)
#  define TRIVIAL_MALLOC_DEBUG
#endif


#if defined(NO_OBMALLOC) || (defined(RPY_STM)&&!defined(TRIVIAL_MALLOC_DEBUG))


/* no special malloc function, use the thread-safe system-provided one */
#define PyObject_Malloc malloc
#define PyObject_Realloc realloc
#define PyObject_Free free


#else


/* allocation functions prototypes */
void *PyObject_Malloc(size_t n);
void *PyObject_Realloc(void *p, size_t n);
void PyObject_Free(void *p);


#ifndef PYPY_NOT_MAIN_FILE

#if defined(TRIVIAL_MALLOC_DEBUG)
  void *PyObject_Malloc(size_t n) { return malloc(n<4?4:n)); }
  void *PyObject_Realloc(void *p, size_t n) { return realloc(p, n<4?4:n); }
  void PyObject_Free(void *p) { if (p) { *((int*)p) = 0xDDDDDDDD; } free(p); }

#elif defined(LINUXMEMCHK)
#  include "linuxmemchk.c"

#else
#  ifndef WITH_PYMALLOC
#    define WITH_PYMALLOC
#  endif
#  include "obmalloc.c"

#endif

#endif
#endif
