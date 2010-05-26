#include <stdlib.h>


#define PyMem_MALLOC(n)		malloc((n) ? (n) : 1)
#define PyMem_REALLOC(p, n)	realloc((p), (n) ? (n) : 1)
#define PyMem_FREE		free

#define PyMem_Malloc PyMem_MALLOC
#define PyMem_Free  PyMem_FREE
#define PyMem_Realloc  PyMem_REALLOC

/*
 * Type-oriented memory interface
 * ==============================
 *
 * Allocate memory for n objects of the given type.  Returns a new pointer
 * or NULL if the request was too large or memory allocation failed.  Use
 * these macros rather than doing the multiplication yourself so that proper
 * overflow checking is always done.
 */

#define PyMem_New(type, n) \
  ( ((n) > PY_SSIZE_T_MAX / sizeof(type)) ? NULL : \
        ( (type *) PyMem_Malloc((n) * sizeof(type)) ) )
#define PyMem_NEW(type, n) \
  ( ((n) > PY_SSIZE_T_MAX / sizeof(type)) ? NULL : \
        ( (type *) PyMem_MALLOC((n) * sizeof(type)) ) )

/*
 * The value of (p) is always clobbered by this macro regardless of success.
 * The caller MUST check if (p) is NULL afterwards and deal with the memory
 * error if so.  This means the original value of (p) MUST be saved for the
 * caller's memory error handler to not lose track of it.
 */
#define PyMem_Resize(p, type, n) \
  ( (p) = ((n) > PY_SSIZE_T_MAX / sizeof(type)) ? NULL : \
        (type *) PyMem_Realloc((p), (n) * sizeof(type)) )
#define PyMem_RESIZE(p, type, n) \
  ( (p) = ((n) > PY_SSIZE_T_MAX / sizeof(type)) ? NULL : \
        (type *) PyMem_REALLOC((p), (n) * sizeof(type)) )

/* PyMem{Del,DEL} are left over from ancient days, and shouldn't be used
 * anymore.  They're just confusing aliases for PyMem_{Free,FREE} now.
 */
#define PyMem_Del               PyMem_Free
#define PyMem_DEL               PyMem_FREE
