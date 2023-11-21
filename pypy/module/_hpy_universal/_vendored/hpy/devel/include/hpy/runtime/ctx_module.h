#ifndef HPY_COMMON_RUNTIME_CTX_MODULE_H
#define HPY_COMMON_RUNTIME_CTX_MODULE_H

#include <Python.h>
#include "hpy.h"

// Helper functions for CPython implementation (both CPython ABI and
// HPy universal module impl for CPython)

/** Converts HPy module definition to CPython module definition for multiphase
 * initialization */
_HPy_HIDDEN PyModuleDef*
_HPyModuleDef_CreatePyModuleDef(HPyModuleDef *hpydef);

/** Converts HPy module definition to PyObject that wraps CPython module
 * definition for multiphase initialization */
_HPy_HIDDEN PyObject*
_HPyModuleDef_AsPyInit(HPyModuleDef *hpydef);

/** Implements the extra HPy specific validation that should be applied to the
 * result of the HPy_mod_create slot. */
_HPy_HIDDEN void
_HPyModule_CheckCreateSlotResult(PyObject **result);

#endif //HPY_COMMON_RUNTIME_CTX_MODULE_H
