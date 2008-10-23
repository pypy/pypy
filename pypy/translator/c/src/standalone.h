
#include <stdlib.h>
#include <limits.h>
#include <assert.h>
#include <math.h>

/* allocation functions prototypes */
void *PyObject_Malloc(size_t n);
void *PyObject_Realloc(void *p, size_t n);
void PyObject_Free(void *p);
