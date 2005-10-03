
/**************************************************************/
/***  this is included before any code produced by genc.py  ***/

/* XXX for now we always include Python.h even to produce stand-alone
 * executables (which are *not* linked against CPython then),
 * to get the convenient macro definitions
 */
#include "Python.h"


#include "thread.h"   /* needs to be included early to define the
                         struct RPyOpaque_ThreadLock */
