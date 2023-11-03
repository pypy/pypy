#ifndef HPy_H
#define HPy_H
#ifdef __cplusplus
extern "C" {
#endif

/* ~~~~~~~~~~~~~~~~ HPy ABI version ~~~~~~~~~~~~~~~ */
// NOTE: these must be kept on sync with the equivalent variables in hpy/devel/abitag.py
/**
 * The ABI version.
 *
 * Minor version N+1 is binary compatible to minor version N. Major versions
 * are not binary compatible (note: HPy can run several binary incompatible
 * versions in one process).
 */
#define HPY_ABI_VERSION 0
#define HPY_ABI_VERSION_MINOR 0
#define HPY_ABI_TAG "hpy0"


/* ~~~~~~~~~~~~~~~~ HPy ABI macros ~~~~~~~~~~~~~~~~ */

/* The following macros are used to determine which kind of module we want to
   compile. The build system must set one of these (e.g. by using `gcc
   -D...`). This is the approach used by the setuptools support provided by
   hpy.devel:

     - HPY_ABI_CPYTHON
     - HPY_ABI_UNIVERSAL
     - HPY_ABI_HYBRID

   In addition we also define HPY_ABI which is a string literal containing a
   string representation of it.
*/

#if defined(HPY_ABI_CPYTHON)
#  if defined(HPY_ABI_HYBRID)
#    error "Conflicting macros are defined: HPY_ABI_CPYTHON and HPY_ABI_HYBRID"
#  endif
#  if defined(HPY_ABI_UNIVERSAL)
#    error "Conflicting macros are defined: HPY_ABI_CPYTHON and HPY_ABI_UNIVERSAL"
#  endif
#  define HPY_ABI "cpython"

#elif defined(HPY_ABI_HYBRID)
#  if defined(HPY_ABI_UNIVERSAL)
#    error "Conflicting macros are defined: HPY_ABI_HYBRID and HPY_ABI_UNIVERSAL"
#  endif
#  define HPY_ABI "hybrid"

#elif defined(HPY_ABI_UNIVERSAL)
#  define HPY_ABI "universal"

#else
#  error "Cannot determine the desired HPy ABI: you must set one of HPY_ABI_CPYTHON, HPY_ABI_UNIVERSAL or HPY_ABI_HYBRID"
#endif


#if defined(HPY_ABI_CPYTHON) || defined(HPY_ABI_HYBRID)
#   define PY_SSIZE_T_CLEAN
#   include <Python.h>
#endif

#include <stdlib.h>
#include <stdint.h>
#include <stdarg.h>

/* ~~~~~~~~~~~~~~~~ useful macros ~~~~~~~~~~~~~~~~ */

#ifdef __GNUC__
#   define _HPy_HIDDEN __attribute__((visibility("hidden")))
#   define _HPy_UNUSED __attribute__((unused))
#else
#   define _HPy_HIDDEN
#   define _HPy_UNUSED
#endif /* __GNUC__ */
#define _HPy_UNUSED_ARG(x) (__HPy_UNUSED_TAGGED ## x) _HPy_UNUSED

#if defined(__clang__) || \
    (defined(__GNUC__) && \
     ((__GNUC__ >= 3) || \
      (__GNUC__ == 2) && (__GNUC_MINOR__ >= 5)))
#  define _HPy_NO_RETURN __attribute__((__noreturn__))
#elif defined(_MSC_VER)
#  define _HPy_NO_RETURN __declspec(noreturn)
#else
#  define _HPy_NO_RETURN
#endif


// clang and gcc supports __has_attribute, MSVC doesn't. This should be enough
// to be able to use it portably
#ifdef __has_attribute
#   define _HPY_compiler_has_attribute(x) __has_attribute(x)
#else
#   define _HPY_compiler_has_attribute(x) 0
#endif

#ifdef HPY_ABI_UNIVERSAL
#  if _HPY_compiler_has_attribute(error)
     // gcc, clang>=14
#    define _HPY_LEGACY __attribute__((error("Cannot use legacy functions when targeting the HPy Universal ABI")))
#  else
     // we don't have any diagnostic feature, too bad
#    define _HPY_LEGACY
#  endif
#else
   // in non-universal modes, we don't attach any attribute
#  define _HPY_LEGACY
#endif

#if defined(_MSC_VER) && defined(__cplusplus) // MSVC C4576
#  define _hconv(h) {h}
#  define _hfconv(h) {h}
#  define _htsconv(h) {h}
#  define _hgconv(h) {h}
#else
#  define _hconv(h) ((HPy){h})
#  define _hfconv(h) ((HPyField){h})
#  define _htsconv(h) ((HPyThreadState){h})
#  define _hgconv(h) ((HPyGlobal){h})
#endif
/* ~~~~~~~~~~~~~~~~ HPyAPI declaration ~~~~~~~~~~~~~~~~ */

/* We have three different kind of API functions: */

/**
 * Public API functions which are exposed to the user, e.g.
 * ``HPy_Add`` or ``HPyType_FromSpec``. Generally speaking they are
 * thin shims dispatching to the actual implementation:
 *
 * * In CPython-ABI mode they directly call the corresponding Py* or
 *   ``HPyAPI_IMPL`` equivalent, e.g. ``PyObject_Add`` or
 *   ``ctx_Type_FromSpec``.
 *
 * * In Universal-ABI mode, they always resolve to an indirect call
 *   through ``HPyContext *``, i.e. ``ctx->ctx_Add(...)``, which on CPython
 *   dispaches to ``ctx_Add``.
 */
#define HPyAPI_FUNC   _HPy_UNUSED static inline

/** An alias for ``HPyAPI_FUNC`` so we can handle it properly in the docs. */
#define HPyAPI_INLINE_HELPER HPyAPI_FUNC

/**
 * CPython implementations for ``HPyAPI_FUNC``
 * functions. Generally speaking, they are put in ctx_*.c files and they are
 * prefixed by ctx\_.
 *
 * Some of these functions are needed by the CPython ABI mode, and by
 * CPython's implementation of hpy.universal: these can be found in
 * hpy/devel/src/runtime/ctx_*.c, e.g. ``ctx_Type_FromSpec`` and
 * ``ctx_Tuple_FromArray``.
 *
 * Some other are used ONLY by ``hpy.universal`` and can be found in
 * hpy/universal/src/ctx_*.c.
 */
#define HPyAPI_IMPL   _HPy_HIDDEN

/**
 * These functions are part of the public API but **not** of
 * the ABI. They are helpers which are meant to be compiled togeher with every
 * extension. E.g. ``HPyArg_Parse`` and ``HPyHelpers_AddType``.
 */
#define HPyAPI_HELPER _HPy_HIDDEN


/* ~~~~~~~~~~~~~~~~ Definition of the type HPy ~~~~~~~~~~~~~~~~ */

/* HPy handles are fully opaque: depending on the implementation, the _i can
   be either an integer or a pointer. A few examples:

   * in CPython ABI mode, ._i is a PyObject*

   * in Universal ABI mode, the meaning of ._i depends on the implementation:

       - CPython (i.e., the code in hpy/universal/src/): ._i is the bitwise
         invert of a PyObject*

       - PyPy: ._i is an index into a list

       - GraalPy: ._i is a tagged value, either an index into a list,
         or an immediate integer or double value

       - Debug mode: _i is a pointer to a DebugHandle, which contains a
         another HPy among other stuff
 */
typedef struct _HPy_s { intptr_t _i; } HPy;
typedef struct { intptr_t _i; } HPyField;
typedef struct { intptr_t _i; } HPyGlobal;
typedef struct { intptr_t _lst; } HPyListBuilder;
typedef struct { intptr_t _tup; } HPyTupleBuilder;
typedef struct { intptr_t _i; } HPyTracker;
typedef struct { intptr_t _i; } HPyThreadState;


/* A null handle is officially defined as a handle whose _i is 0. This is true
   in all ABI modes. */
#define HPy_NULL _hconv(0)
#define HPy_IsNull(h) ((h)._i == 0)

#define HPyField_NULL _hfconv(0)
#define HPyField_IsNull(f) ((f)._i == 0)

/* Convenience functions to cast between HPy and void*.  We need to decide
   whether these are part of the official API or not, and maybe introduce a
   better naming convention. For now, they are needed for ujson. */
static inline HPy HPy_FromVoidP(void *p) { return _hconv((intptr_t)p); }
static inline void* HPy_AsVoidP(HPy h) { return (void*)h._i; }


/* ~~~~~~~~~~~~~~~~ Definition of other types ~~~~~~~~~~~~~~~~ */

typedef struct _HPyContext_s HPyContext;

/** An enumeration of the different kinds of source code strings. */
typedef enum {
    /** Parse isolated expressions (e.g. ``a + b``). */
    HPy_SourceKind_Expr = 0,

    /**
     * Parse sequences of statements as read from a file or other source. This
     * is the symbol to use when compiling arbitrarily long Python source code.
     */
    HPy_SourceKind_File = 1,

    /**
     * Parse a single statement. This is the mode used for the interactive
     * interpreter loop.
     */
    HPy_SourceKind_Single = 2,
} HPy_SourceKind;

#ifdef HPY_ABI_CPYTHON
    typedef Py_ssize_t HPy_ssize_t;
    typedef Py_hash_t HPy_hash_t;
    typedef Py_UCS4 HPy_UCS4;

#   define HPY_SSIZE_T_MAX PY_SSIZE_T_MAX
#   define HPY_SSIZE_T_MIN PY_SSIZE_T_MIN

#else
    typedef intptr_t HPy_ssize_t;
    typedef intptr_t HPy_hash_t;
    typedef uint32_t HPy_UCS4;

#   define HPY_SSIZE_T_MAX INTPTR_MAX
#   define HPY_SSIZE_T_MIN (-HPY_SSIZE_T_MAX-1)

    /* HPyCapsule field keys */
    typedef enum {
        HPyCapsule_key_Pointer = 0,
        HPyCapsule_key_Name = 1,
        HPyCapsule_key_Context = 2,
        HPyCapsule_key_Destructor = 3,
    } _HPyCapsule_key;
#endif


/* ~~~~~~~~~~~~~~~~ Additional #includes ~~~~~~~~~~~~~~~~ */

#include "hpy/cpy_types.h"
#include "hpy/hpyexports.h"
#include "hpy/macros.h"
#include "hpy/hpyfunc.h"
#include "hpy/hpydef.h"
#include "hpy/hpytype.h"
#include "hpy/hpymodule.h"
#include "hpy/runtime/argparse.h"
#include "hpy/runtime/buildvalue.h"
#include "hpy/runtime/format.h"
#include "hpy/runtime/helpers.h"
#include "hpy/runtime/structseq.h"

#ifdef HPY_ABI_CPYTHON
#   include "hpy/cpython/autogen_ctx.h"
#   include "hpy/runtime/ctx_funcs.h"
#   include "hpy/runtime/ctx_type.h"
#   include "hpy/cpython/misc.h"
#   include "hpy/cpython/autogen_api_impl.h"
#else
#   include "hpy/universal/autogen_ctx.h"
#   include "hpy/universal/autogen_trampolines.h"
#   include "hpy/universal/misc_trampolines.h"
#endif

#include "hpy/inline_helpers.h"

#ifdef __cplusplus
}
#endif
#endif /* HPy_H */
