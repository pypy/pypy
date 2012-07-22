/* allocation functions prototypes */
void *PyObject_Malloc(size_t n);
void *PyObject_Realloc(void *p, size_t n);
void PyObject_Free(void *p);

/***  tracking raw mallocs and frees for debugging          ***/

#ifndef RPY_ASSERT

#  define OP_TRACK_ALLOC_START(addr, r)   /* nothing */
#  define OP_TRACK_ALLOC_STOP(addr, r)    /* nothing */
#  define pypy_debug_alloc_results() /* nothing */

#else /* RPY_ASSERT */

#  define OP_TRACK_ALLOC_START(addr, r)  pypy_debug_alloc_start(addr, \
                                                                __FUNCTION__)
#  define OP_TRACK_ALLOC_STOP(addr, r)   pypy_debug_alloc_stop(addr)

void pypy_debug_alloc_start(void*, const char*);
void pypy_debug_alloc_stop(void*);
void pypy_debug_alloc_results(void);

#endif /* RPY_ASSERT */

