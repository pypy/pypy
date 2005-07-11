
/************************************************************/
/***  C header file for code produced by genc.py          ***/

#include "Python.h"
#include "compile.h"
#include "frameobject.h"
#include "structmember.h"
#include "traceback.h"
#include "marshal.h"
#include "eval.h"

#include "src/exception.h"
#include "src/trace.h"
#include "src/support.h"
#include "src/module.h"

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
#endif
