
/**************************************************************/
/***  this is included before any code produced by genc.py  ***/


#include "src/commondefs.h"

#ifdef _WIN32
#  include <io.h>   /* needed, otherwise _lseeki64 truncates to 32-bits (??) */
#endif

#include <stddef.h>


#include "src/align.h"
