
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

#include "src/mem.h"
#include "src/exception.h"
#include "src/support.h"
#ifndef PY_LONG_LONG
#define PY_LONG_LONG long long
#endif

#ifndef PYPY_STANDALONE
#  include "src/pyobj.h"
#endif

#include "src/int.h"
#include "src/char.h"
#include "src/float.h"
#include "src/address.h"
#ifndef AVR
#include "src/unichar.h"
#endif
#include "src/llgroup.h"

#include "src/instrument.h"

/* optional assembler bits */
#if defined(__GNUC__) && defined(__i386__)
#  include "src/asm_gcc_x86.h"
#endif

#if defined(__GNUC__) && defined(__ppc__)
#  include "src/asm_ppc.h"
#endif


/*** modules ***/
#ifdef HAVE_RTYPER      /* only if we have an RTyper */
#  include "src/rtyper.h"
#  include "src/debug_print.h"
#  include "src/debug_traceback.h"
#ifndef AVR
#  include "src/ll_os.h"
#  include "src/ll_strtod.h"
#  ifdef RPyExc_thread_error
#    include "src/ll_thread.h"
#  endif
#endif
#endif

#ifdef PYPY_STANDALONE
#  include "src/allocator.h"
#  include "src/main.h"
#endif

/* suppress a few warnings in the generated code */
#ifdef MS_WINDOWS
#  ifdef _MSC_VER
#    pragma warning(disable: 4033 4102 4101 4716)
#  endif
#endif
