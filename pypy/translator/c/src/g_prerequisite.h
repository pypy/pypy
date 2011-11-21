
/**************************************************************/
/***  this is included before any code produced by genc.py  ***/

#ifdef PYPY_STANDALONE
#  include "src/commondefs.h"
#else
#  include "Python.h"
#endif

#ifdef _WIN64
#  define Signed __int64
#  define SIGNED_MIN LLONG_MIN 
#else
#  define Signed long
#  define SIGNED_MIN LONG_MIN
#endif
#define Unsigned unsigned Signed

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
