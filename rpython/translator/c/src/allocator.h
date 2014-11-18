
#if defined(RPY_STM) && defined(RPY_STM_ASSERT)
#  define PYPY_USE_TRIVIAL_MALLOC
#endif

#if defined(RPY_STM) && !defined(PYPY_USE_TRIVIAL_MALLOC)
#  define PYPY_NO_OBMALLOC
#endif

#ifdef PYPY_NO_OBMALLOC
/* no special malloc function, use the thread-safe system-provided one */
#define PyObject_Malloc malloc
#define PyObject_Realloc realloc
#define PyObject_Free free
#else
/* allocation functions prototypes */
RPY_EXTERN void *PyObject_Malloc(size_t n);
RPY_EXTERN void *PyObject_Realloc(void *p, size_t n);
RPY_EXTERN void PyObject_Free(void *p);
#endif
