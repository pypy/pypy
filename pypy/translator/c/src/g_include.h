
/************************************************************/
/***  C header file for code produced by genc.py          ***/

/* XXX for now we always include Python.h even to produce stand-alone
 * executables (which are *not* linked against CPython then),
 * to get the convenient macro definitions
 */
#include "Python.h"
#ifndef PYPY_STANDALONE
#  include "compile.h"
#  include "frameobject.h"
#  include "structmember.h"
#  include "traceback.h"
#  include "marshal.h"
#  include "eval.h"
#else
#  include "src/standalone.h"
#endif

#include "src/exception.h"
#include "src/trace.h"
#include "src/support.h"

#ifndef PYPY_STANDALONE
#  include "src/module.h"
#endif

#include "src/mem.h"
#include "src/int.h"
#include "src/char.h"
#include "src/unichar.h"
#include "src/float.h"
#include "src/pyobj.h"

/*** modules ***/
#ifdef HAVE_RTYPER      /* only if we have an RTyper */
#  include "src/rtyper.h"
#  include "src/ll_os.h"
#  include "src/ll_time.h"
#  include "src/ll_math.h"
#endif

#ifdef PYPY_STANDALONE
#  include "src/main.h"
#endif

