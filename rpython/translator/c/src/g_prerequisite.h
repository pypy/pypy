
/**************************************************************/
/***  this is included before any code produced by genc.py  ***/


#include "src/commondefs.h"

#ifdef _WIN32
#  include <io.h>   /* needed, otherwise _lseeki64 truncates to 32-bits (??) */
#endif

#include <stddef.h>


#ifdef __GNUC__       /* other platforms too, probably */
typedef _Bool bool_t;
# define RPY_LENGTH0     0       /* array decl [0] are ok  */
# define RPY_DUMMY_VARLENGTH     char _dummy[0];
#else
typedef unsigned char bool_t;
# define RPY_LENGTH0     1       /* array decl [0] are bad */
# define RPY_DUMMY_VARLENGTH     /* nothing */
#endif
/* use [1] (C89 struct hack) rather than [] (C99 FAM) to avoid GCC placing
   a struct-with-FAM inside a union, which GCC 14 handles more strictly */
# define RPY_VARLENGTH   1

#ifdef RPY_REVERSE_DEBUGGER
#include "src-revdb/revdb_preinclude.h"
#endif
