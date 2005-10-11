
/************************************************************/
/***  C header file for code produced by genc.py          ***/

#ifndef PYPY_STANDALONE
#  include "Python.h"
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
#include "src/address.h"

/*** modules ***/
#ifdef HAVE_RTYPER      /* only if we have an RTyper */
#  include "src/rtyper.h"
#  include "src/ll_os.h"
#  include "src/ll_time.h"
#  include "src/ll_math.h"
#  include "src/ll_strtod.h"
#  include "src/ll_thread.h"
#  include "src/ll_stackless.h"
#endif

#ifdef PYPY_STANDALONE
#  include "src/main.h"
#endif

/* suppress a few warnings in the generated code */
#ifdef MS_WINDOWS
#  ifdef _MSC_VER
#    pragma warning(disable: 4033 4102 4101 4716)
#  endif
#endif
