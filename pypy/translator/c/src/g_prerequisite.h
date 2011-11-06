
/**************************************************************/
/***  this is included before any code produced by genc.py  ***/

#ifdef PYPY_STANDALONE
#  include "src/commondefs.h"
#else
#  include "Python.h"
#endif

#ifdef _WIN64
#  define new_long __int64
#  define NEW_LONG_MIN LLONG_MIN
#  define NEW_LONG_MAX LLONG_MAX
#else
#  define new_log long
#  define NEW_LONG_MIN LONG_MIN
#  define NEW_LONG_MAX LONG_MAX
#endif

#ifdef _WIN32
#  include <io.h>   /* needed, otherwise _lseeki64 truncates to 32-bits (??) */
#endif

#include "thread.h"   /* needs to be included early to define the
                         struct RPyOpaque_ThreadLock */

#include <stddef.h>


#ifdef __GNUC__       /* other platforms too, probably */
typedef _Bool bool_t;
#else
typedef unsigned char bool_t;
#endif


#include "src/align.h"
