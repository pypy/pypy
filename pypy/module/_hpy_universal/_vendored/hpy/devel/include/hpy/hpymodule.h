#ifndef HPY_UNIVERSAL_HPYMODULE_H
#define HPY_UNIVERSAL_HPYMODULE_H

/* If 'HPY_EMBEDDED_MODULES' is defined, this means that there will be several
   embedded HPy modules (and so, several 'HPy_MODINIT' usages) in the same
   binary. In this case, some restrictions apply: (1) all of the module's
   methods/member/slots/... must be defined in the same file, and (2) the
   embedder *MUST* declare the module to be "embeddable" by using macro
   'HPY_MOD_EMBEDDABLE(modname)'. */
#ifdef HPY_EMBEDDED_MODULES
#define _HPy_CTX_MODIFIER static
#define HPY_MOD_EMBEDDABLE(modname) \
    _HPy_CTX_MODIFIER HPyContext *_ctx_for_trampolines;
#else
#define _HPy_CTX_MODIFIER _HPy_HIDDEN
/**
 * Declares a module to be *embeddable* which means that it and its members can
 * be compiled/linked into a binary together with other embeddable HPy modules.
 *
 * You may declare a module to be *embeddable* if all of its member definitions
 * are in the same file.
 */
#define HPY_MOD_EMBEDDABLE(modname)
// this is defined by HPy_MODINIT
extern HPyContext *_ctx_for_trampolines;
#endif


/**
 * Definition of a Python module. Pointer to this struct is returned from
 * the HPy initialization function ``HPyInit_{extname}`` and the Python
 * interpreter creates a Python module from it. HPy supports only the
 * multi-phase module initialization approach (PEP 451).
 *
 * There is no HPy API to create a Python module manually, i.e., equivalent
 * of ``PyModule_Create`` or ``PyModule_FromDefAndSpec``, for the time being,
 * but may be added if a use-case arises.
 *
 * Note: unlike Python/C API, HPy module definition does not specify module
 * name. The name if always taken from the ModuleSpec, which is also the case
 * in multi-phase module initialization on Python/C API.
 */
typedef struct {
    /** Docstring of the type (UTF-8 encoded; may be ``NULL``) */
    const char* doc;

    /**
     * The size  (in bytes) of the module state structure. If set to zero,
     * then the module will not get allocated and assigned any HPy module state.
     * Negative size, unlike in Python/C API, does not have any specific meaning
     * and will produce a runtime error.
     */
    HPy_ssize_t size;

    /**
     * ``NULL``-terminated list of legacy module-level methods.
     * In order to enable incremental migration
     * from C API to HPy, it is possible to still add *legacy* method
     * definitions. Those methods have a C API signature which means that they
     * still receive ``PyObject *`` and similar arguments. If legacy methods
     * are defined, you cannot create a *universal binary* (i.e. a binary that
     * will run on all Python engines).
     */
    cpy_PyMethodDef *legacy_methods;

    /**
     * Pointer to a ``NULL``-terminated array of pointers to HPy defines (i.e.
     * ``HPyDef *``). Note, that some kinds of HPy definitions don't make sense
     * for a module. In particular, anything else than methods.
     */
    HPyDef **defines;

    /**
     * Pointer to a ``NULL``-terminated array of pointers to
     * :c:struct:`HPyGlobal` variables. For details, see :doc:`hpy-global`.
     */
    HPyGlobal **globals;
} HPyModuleDef;


#if defined(__cplusplus)
#  define HPy_EXPORTED_FUNC extern "C" HPy_EXPORTED_SYMBOL
#else /* __cplusplus */
#  define HPy_EXPORTED_FUNC HPy_EXPORTED_SYMBOL
#endif /* __cplusplus */

#ifdef HPY_ABI_CPYTHON

// helpers provided by HPy runtime:
#include "hpy/runtime/ctx_module.h"

// module initialization in the CPython case
#define HPy_MODINIT(ext_name, mod_def)                         \
    PyMODINIT_FUNC                                             \
    PyInit_##ext_name(void)                                    \
    {                                                          \
        return _HPyModuleDef_AsPyInit(&mod_def);               \
    }

#else // HPY_ABI_CPYTHON

// module initialization in the universal and hybrid case

/**
 * Convenience macro for generating the module initialization code. This will
 * generate three functions that are used by to verify an initialize the module
 * when loading:
 *
 * ``get_required_hpy_major_version_<modname>``
 *   The HPy major version this module was built with.
 *
 * ``get_required_hpy_minor_version_<modname>``
 *   The HPy minor version this module was built with.
 *
 * ``HPyModuleDef* HPyInit_<extname>``
 *   The init function that will be called by the interpreter. This function
 *   does not have an access to HPyContext and thus cannot call any HPy APIs.
 *   The purpose of this function is to return a pointer to a HPyModuleDef
 *   structure that will serve as a specification of the module that should be
 *   created by the interpreter. HPy supports only multi-phase module
 *   initialization (PEP 451). Any module initialization code can be added
 *   to the HPy_mod_exec slot of the module if needed.
 *
 * Example:
 *
 * .. code-block:: c
 *
 *   HPy_MODINIT(myextension_shared_library_filename, my_hpy_module_def)
 */
#define HPy_MODINIT(ext_name, mod_def)                         \
    HPy_EXPORTED_FUNC uint32_t                                 \
    get_required_hpy_major_version_##ext_name(void);           \
    HPy_EXPORTED_FUNC uint32_t                                 \
    get_required_hpy_major_version_##ext_name()                \
    {                                                          \
        return HPY_ABI_VERSION;                                \
    }                                                          \
    HPy_EXPORTED_FUNC uint32_t                                 \
    get_required_hpy_minor_version_##ext_name(void);           \
    uint32_t                                                   \
    get_required_hpy_minor_version_##ext_name(void)            \
    {                                                          \
        return HPY_ABI_VERSION_MINOR;                          \
    }                                                          \
    _HPy_CTX_MODIFIER HPyContext *_ctx_for_trampolines;        \
    HPy_EXPORTED_FUNC void                                     \
    HPyInitGlobalContext_##ext_name(HPyContext *ctx)           \
    {                                                          \
        _ctx_for_trampolines = ctx;                            \
    }                                                          \
    HPy_EXPORTED_FUNC HPyModuleDef*                            \
    HPyInit_##ext_name(void);                                  \
    HPyModuleDef *HPyInit_##ext_name()                         \
    {                                                          \
        return &mod_def;                                       \
    }

// Implementation note: the global HPyContext is used by the CPython
// trampolines generated by the HPyDef_XXX macros

#endif // HPY_ABI_CPYTHON

#endif // HPY_UNIVERSAL_HPYMODULE_H
