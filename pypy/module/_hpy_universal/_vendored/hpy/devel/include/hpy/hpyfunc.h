#ifndef HPY_UNIVERSAL_HPYFUNC_H
#define HPY_UNIVERSAL_HPYFUNC_H

typedef enum {
    HPyFunc_VARARGS  = 1,  // METH_FASTCALL
    HPyFunc_KEYWORDS = 2,  // METH_FASTCALL | METH_KEYWORDS
    HPyFunc_NOARGS   = 3,  // METH_NOARGS
    HPyFunc_O        = 4,  // METH_O

    HPyFunc_DESTROYFUNC,

    HPyFunc_GETBUFFERPROC,
    HPyFunc_RELEASEBUFFERPROC,
    HPyFunc_UNARYFUNC,
    HPyFunc_BINARYFUNC,
    HPyFunc_TERNARYFUNC,
    HPyFunc_INQUIRY,
    HPyFunc_LENFUNC,
    HPyFunc_SSIZEARGFUNC,
    HPyFunc_SSIZESSIZEARGFUNC,
    HPyFunc_SSIZEOBJARGPROC,
    HPyFunc_SSIZESSIZEOBJARGPROC,
    HPyFunc_OBJOBJARGPROC,
    HPyFunc_FREEFUNC,
    HPyFunc_GETATTRFUNC,
    HPyFunc_GETATTROFUNC,
    HPyFunc_SETATTRFUNC,
    HPyFunc_SETATTROFUNC,
    HPyFunc_REPRFUNC,
    HPyFunc_HASHFUNC,
    HPyFunc_RICHCMPFUNC,
    HPyFunc_GETITERFUNC,
    HPyFunc_ITERNEXTFUNC,
    HPyFunc_DESCRGETFUNC,
    HPyFunc_DESCRSETFUNC,
    HPyFunc_INITPROC,
    HPyFunc_NEWFUNC,
    HPyFunc_GETTER,
    HPyFunc_SETTER,
    HPyFunc_OBJOBJPROC,
    HPyFunc_TRAVERSEPROC,
    HPyFunc_DESTRUCTOR,
    HPyFunc_CAPSULE_DESTRUCTOR,
    HPyFunc_VECTORCALLFUNC,

    HPyFunc_MOD_CREATE,

} HPyFunc_Signature;

/* The typedefs corresponding to the various HPyFunc_Signature members
   are produced inside autogen_hpyfunc_declare.h. */


/* ~~~ HPyFunc_DECLARE ~~~

   Emit a forward declaration for a function SYM having a signature SIG, where
   SIG is one of HPyFunc_Signature members.

   Strictly speaking, the anonymous enum is not needed, since it just defines
   a constant like Foo_sig which is never used anyway. However, since we try
   to use "SIG" in the enum definition, we get a very nice error message in
   case we use a SIG value which does not exists.  If we didn't use this
   trick, we would get a VERY obscure error message, since gcc would see a
   function call to something like _HPyFunc_DECLARE_HPyFunc_XXX.
*/
#define HPyFunc_DECLARE(SYM, SIG) \
    enum { SYM##_sig = SIG };     \
    _HPyFunc_DECLARE_##SIG(SYM)


/* ~~~ HPyFunc_TRAMPOLINE ~~~

   Emit a CPython-compatible trampoline which calls IMPL, where IMPL has the
   signature SIG. See above for why we need the anonymous enum. The actual
   implementation of trampolines are in hpyfunc_trampolines.h, which is
   different for the CPython and Universal cases
*/
#define HPyFunc_TRAMPOLINE(SYM, IMPL, SIG) \
    enum { SYM##_sig = SIG };              \
    _HPyFunc_TRAMPOLINE_##SIG(SYM, IMPL)

typedef struct {
    void *buf;
    HPy obj;        /* owned reference */
    HPy_ssize_t len;
    HPy_ssize_t itemsize;
    int readonly;
    int ndim;
    char *format;
    HPy_ssize_t *shape;
    HPy_ssize_t *strides;
    HPy_ssize_t *suboffsets;
    void *internal;
} HPy_buffer;

typedef int (*HPyFunc_visitproc)(HPyField *, void *);

/* COPIED AND ADAPTED FROM CPython.
 * Utility macro to help write tp_traverse functions
 * To use this macro, the tp_traverse function must name its arguments
 * "visit" and "arg".  This is intended to keep tp_traverse functions
 * looking as much alike as possible.
 */
#define HPy_VISIT(hpyfield)                                             \
    do {                                                                \
        if (!HPyField_IsNull(*hpyfield)) {                              \
            int vret = visit(hpyfield, arg);                            \
            if (vret)                                                   \
                return vret;                                            \
            }                                                           \
    } while (0)



#include "autogen_hpyfunc_declare.h"

#ifdef HPY_ABI_CPYTHON
#  include "cpython/hpyfunc_trampolines.h"
#  include "cpython/autogen_hpyfunc_trampolines.h"
#else
#  include "universal/hpyfunc_trampolines.h"
#  include "universal/autogen_hpyfunc_trampolines.h"
#endif // HPY_ABI_CPYTHON

#endif /* HPY_UNIVERSAL_HPYFUNC_H */
