#ifdef PYPY_STANDALONE 
/* allocation functions prototypes */
void *PyObject_Malloc(size_t n);
void *PyObject_Realloc(void *p, size_t n);
void PyObject_Free(void *p);

#endif  /* PYPY_STANDALONE */
