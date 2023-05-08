#include <Python.h>
#include "hpy.h"
#include "hpy/runtime/ctx_type.h"

#ifndef HPY_ABI_CPYTHON
   // for _h2py and _py2h
#  include "handles.h"
#endif

#define NON_DEFAULT_MESSAGE \
    "This is not allowed because custom " \
    "HPy_mod_create slot cannot return a builtin module " \
    "object and cannot make any use of any other data " \
    "defined in the HPyModuleDef. Either do not define " \
    "HPy_mod_create slot and let the runtime create a builtin " \
    "module object from the provided HPyModuleDef, or do not define " \
    "anything else but the HPy_mod_create slot."

static PyModuleDef empty_moduledef = {
    PyModuleDef_HEAD_INIT
};

static PyModuleDef_Slot* create_mod_slots(HPyModuleDef *hpydef, bool *found_create)
{
    size_t slots_count = 0;
    bool found_non_create = false;
    for (int i = 0; hpydef->defines[i] != NULL; i++) {
        HPyDef *src = hpydef->defines[i];
        if (src->kind != HPyDef_Kind_Slot) {
            found_non_create = true;
            continue;
        }
        slots_count++;
        if (src->slot.slot == HPy_mod_create) {
            if (*found_create) {
                PyErr_SetString(PyExc_SystemError, "Multiple definitions "
                                                   "of the HPy_mod_create "
                                                   "slot in HPyModuleDef.defines.");
                return NULL;
            }
            *found_create = true;
        } else if (src->slot.slot != HPy_mod_exec) {
            PyErr_Format(PyExc_SystemError, "Unsupported slot in "
                                            "HPyModuleDef.defines (value: %d).",
                         (int) src->slot.slot);
            return NULL;
        } else {
            assert(src->slot.slot == HPy_mod_exec);
            found_non_create = true;
        }
    }
    if (*found_create && found_non_create) {
        PyErr_Format(PyExc_SystemError,
                     "HPyModuleDef defines a HPy_mod_create slot and some other "
                     "slots or methods. " NON_DEFAULT_MESSAGE);
        return NULL;
    }

    PyModuleDef_Slot* m_slots = (PyModuleDef_Slot*)PyMem_Calloc(
            slots_count + 1, sizeof(PyModuleDef_Slot));
    m_slots[slots_count].slot = 0;
    m_slots[slots_count].value = NULL;
    size_t slot_index = 0;
    for (int i = 0; hpydef->defines[i] != NULL; i++) {
        HPyDef *src = hpydef->defines[i];
        if (src->kind != HPyDef_Kind_Slot)
            continue;
        int py_slot;
        if (src->slot.slot == HPy_mod_create) {
            py_slot = Py_mod_create;
        } else {
            assert(src->slot.slot == HPy_mod_exec);
            py_slot = Py_mod_exec;
        }
        m_slots[slot_index].slot = py_slot;
        m_slots[slot_index].value = (void*) src->slot.cpy_trampoline;
        slot_index++;
    }
    return m_slots;
}

_HPy_HIDDEN PyModuleDef*
_HPyModuleDef_CreatePyModuleDef(HPyModuleDef *hpydef)
{
    PyModuleDef *def = (PyModuleDef*)PyMem_Malloc(sizeof(PyModuleDef));
    if (def == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    memcpy(def, &empty_moduledef, sizeof(PyModuleDef));
    def->m_doc = hpydef->doc;
    if (hpydef->size < 0) {
        PyErr_SetString(PyExc_SystemError, "HPy does not permit "
                                           "HPyModuleDef.size < 0");
        goto error;
    } else if (hpydef->size > 0) {
        // GH-328
        PyErr_SetString(PyExc_SystemError, "Module state is not supported yet "
                                           "in HPy, set HPyModuleDef.size = 0 "
                                           "if module state is not needed");
        goto error;
    }

    def->m_methods = create_method_defs(hpydef->defines, hpydef->legacy_methods);
    if (def->m_methods == NULL) {
        goto error;
    }

    if (hpydef->defines != NULL) {
        bool found_create = false;
        def->m_slots = create_mod_slots(hpydef, &found_create);
        if (def->m_slots == NULL) {
            goto error;
        }
        if (found_create && (hpydef->legacy_methods || hpydef->size > 0 ||
            hpydef->doc != NULL || hpydef->globals != NULL)) {
            PyErr_Format(PyExc_SystemError,
                         "HPyModuleDef defines a HPy_mod_create slot and some "
                         "of the other fields are not set to their default "
                         "value. " NON_DEFAULT_MESSAGE);
            goto error;
        }
    }

    return def;
error:
    if (def != NULL) {
        PyMem_Free(def);
    }
    return NULL;
}

_HPy_HIDDEN PyObject*
_HPyModuleDef_AsPyInit(HPyModuleDef *hpydef)
{
    PyModuleDef *def = _HPyModuleDef_CreatePyModuleDef(hpydef);
    if (def == NULL) {
        return NULL;
    }
    return PyModuleDef_Init(def);
}

_HPy_HIDDEN void
_HPyModule_CheckCreateSlotResult(PyObject **result)
{
    if (*result != NULL && PyModule_Check(*result)) {
        PyErr_SetString(PyExc_SystemError,
                        "HPy_mod_create slot returned a builtin module object. "
                        "This is currently not supported.");
        *result = NULL;
    }
}
