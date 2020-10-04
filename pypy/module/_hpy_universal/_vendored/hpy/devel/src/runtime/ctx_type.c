#include <stddef.h>
#include <Python.h>
#include "structmember.h" // for PyMemberDef
#include "hpy.h"
#include "common/runtime/ctx_type.h"

#ifdef HPY_UNIVERSAL_ABI
   // for _h2py and _py2h
#  include "handles.h"
#endif


_HPy_HIDDEN void*
ctx_Cast(HPyContext ctx, HPy h)
{
    return _h2py(h);
}

static int
sig2flags(HPyFunc_Signature sig)
{
    switch(sig) {
        case HPyFunc_VARARGS:  return METH_VARARGS;
        case HPyFunc_KEYWORDS: return METH_VARARGS | METH_KEYWORDS;
        case HPyFunc_NOARGS:   return METH_NOARGS;
        case HPyFunc_O:        return METH_O;
        default:               return -1;
    }
}

static HPy_ssize_t
HPyDef_count(HPyDef *defs[], HPyDef_Kind kind)
{
    HPy_ssize_t res = 0;
    if (defs == NULL)
        return res;
    for(int i=0; defs[i] != NULL; i++)
        if (defs[i]->kind == kind)
            res++;
    return res;
}

static void
legacy_slots_count(PyType_Slot slots[], HPy_ssize_t *slot_count,
                   PyMethodDef **method_defs, PyMemberDef **member_defs,
                   PyGetSetDef **getset_defs)
{
    *slot_count = 0;
    *method_defs = NULL;
    *member_defs = NULL;
    *getset_defs = NULL;
    if (slots == NULL)
        return;
    for(int i=0; slots[i].slot != 0; i++)
        switch(slots[i].slot) {
        case Py_tp_methods:
            *method_defs = (PyMethodDef *)slots[i].pfunc;
            break;
        case Py_tp_members:
            *member_defs = (PyMemberDef *)slots[i].pfunc;
            break;
        case Py_tp_getset:
            *getset_defs = (PyGetSetDef *)slots[i].pfunc;
            break;
        default:
            (*slot_count)++;
            break;
        }
}

static int
hpy_slot_to_cpy_slot(HPySlot_Slot src)
{
    switch (src) {
        case HPy_tp_destroy: return Py_tp_dealloc;
        default: return src;   /* same numeric value by default */
    }
}


/*
 * Create a PyMethodDef which contains:
 *     1. All HPyMeth contained in hpyspec->defines
 *     2. All the PyMethodDef contained inside legacy_methods
 *
 * Notes:
 *     - This function is also called from ctx_module.c.
 *     - This malloc()s a result which will never be freed. Too bad
 */
_HPy_HIDDEN PyMethodDef *
create_method_defs(HPyDef *hpydefs[], PyMethodDef *legacy_methods)
{
    HPy_ssize_t hpymeth_count = HPyDef_count(hpydefs, HPyDef_Kind_Meth);
    // count the legacy methods
    HPy_ssize_t legacy_count = 0;
    if (legacy_methods != NULL) {
        while (legacy_methods[legacy_count].ml_name != NULL)
            legacy_count++;
    }
    HPy_ssize_t total_count = hpymeth_count + legacy_count;

    // allocate&fill the result
    PyMethodDef *result = PyMem_Calloc(total_count+1, sizeof(PyMethodDef));
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    // copy the HPy methods
    int dst_idx = 0;
    if (hpydefs != NULL) {
        for(int i=0; hpydefs[i] != NULL; i++) {
            HPyDef *src = hpydefs[i];
            if (src->kind != HPyDef_Kind_Meth)
                continue;
            PyMethodDef *dst = &result[dst_idx++];
            dst->ml_name = src->meth.name;
            dst->ml_meth = src->meth.cpy_trampoline;
            dst->ml_flags = sig2flags(src->meth.signature);
            if (dst->ml_flags == -1) {
                PyMem_Free(result);
                PyErr_SetString(PyExc_ValueError,
                                "Unsupported HPyMeth signature");
                return NULL;
            }
            dst->ml_doc = src->meth.doc;
        }
    }
    // copy the legacy methods
    for(int i=0; i<legacy_count; i++)
        result[dst_idx++] = legacy_methods[i];
    result[dst_idx++] = (PyMethodDef){NULL, NULL, 0, NULL};
    if (dst_idx != total_count + 1)
        Py_FatalError("bogus count in create_method_defs");
    return result;
}

static PyMemberDef *
create_member_defs(HPyDef *hpydefs[], PyMemberDef *legacy_members)
{
    HPy_ssize_t hpymember_count = HPyDef_count(hpydefs, HPyDef_Kind_Member);
    // count the legacy members
    HPy_ssize_t legacy_count = 0;
    if (legacy_members != NULL) {
        while (legacy_members[legacy_count].name != NULL)
            legacy_count++;
    }
    HPy_ssize_t total_count = hpymember_count + legacy_count;

    // allocate&fill the result
    PyMemberDef *result = PyMem_Calloc(total_count+1, sizeof(PyMemberDef));
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    // copy the HPy members
    int dst_idx = 0;
    if (hpydefs != NULL) {
        for(int i=0; hpydefs[i] != NULL; i++) {
            HPyDef *src = hpydefs[i];
            if (src->kind != HPyDef_Kind_Member)
                continue;
            PyMemberDef *dst = &result[dst_idx++];
            /* for Python <= 3.6 compatibility, we need to remove the 'const'
               qualifier from src->member.{name,doc} */
            dst->name = (char *)src->member.name;
            dst->type = src->member.type;
            dst->offset = src->member.offset;
            dst->doc = (char *)src->member.doc;
            if (src->member.readonly)
                dst->flags = READONLY;
            else
                dst->flags = 0; // read-write
        }
    }
    // copy the legacy members
    for(int i=0; i<legacy_count; i++)
        result[dst_idx++] = legacy_members[i];
    result[dst_idx++] = (PyMemberDef){NULL};
    if (dst_idx != total_count + 1)
        Py_FatalError("bogus count in create_member_defs");
    return result;
}

static PyGetSetDef *
create_getset_defs(HPyDef *hpydefs[], PyGetSetDef *legacy_getsets)
{
    HPy_ssize_t hpygetset_count = HPyDef_count(hpydefs, HPyDef_Kind_GetSet);
    // count the legacy members
    HPy_ssize_t legacy_count = 0;
    if (legacy_getsets != NULL) {
        while (legacy_getsets[legacy_count].name != NULL)
            legacy_count++;
    }
    HPy_ssize_t total_count = hpygetset_count + legacy_count;

    // allocate&fill the result
    PyGetSetDef *result = PyMem_Calloc(total_count+1, sizeof(PyGetSetDef));
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    // copy the HPy members
    int dst_idx = 0;
    if (hpydefs != NULL) {
        for(int i=0; hpydefs[i] != NULL; i++) {
            HPyDef *src = hpydefs[i];
            if (src->kind != HPyDef_Kind_GetSet)
                continue;
            PyGetSetDef *dst = &result[dst_idx++];
            /* for Python <= 3.6 compatibility, we need to remove the 'const'
               qualifier from src->getset.{name,doc} */
            dst->name = (char *)src->getset.name;
            dst->get = src->getset.getter_cpy_trampoline;
            dst->set = src->getset.setter_cpy_trampoline;
            dst->doc = (char *)src->getset.doc;
            dst->closure = src->getset.closure;
        }
    }
    // copy the legacy members
    for(int i=0; i<legacy_count; i++)
        result[dst_idx++] = legacy_getsets[i];
    result[dst_idx++] = (PyGetSetDef){NULL};
    if (dst_idx != total_count + 1)
        Py_FatalError("bogus count in create_getset_defs");
    return result;
}


static PyType_Slot *
create_slot_defs(HPyType_Spec *hpyspec)
{
    HPy_ssize_t hpyslot_count = HPyDef_count(hpyspec->defines, HPyDef_Kind_Slot);
    // add the legacy slots
    HPy_ssize_t legacy_slot_count = 0;
    PyMethodDef *legacy_method_defs = NULL;
    PyMemberDef *legacy_member_defs = NULL;
    PyGetSetDef *legacy_getset_defs = NULL;
    legacy_slots_count(hpyspec->legacy_slots, &legacy_slot_count,
                       &legacy_method_defs, &legacy_member_defs,
                       &legacy_getset_defs);

    // add slots to hold Py_tp_methods, Py_tp_members, Py_tp_getset
    hpyslot_count += 3;

    // allocate the result PyType_Slot array
    HPy_ssize_t total_slot_count = hpyslot_count + legacy_slot_count;
    PyType_Slot *result = PyMem_Calloc(total_slot_count+1, sizeof(PyType_Slot));
    if (result == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    // fill the result with non-meth, non-member, non-getset slots
    int dst_idx = 0;
    if (hpyspec->defines != NULL) {
        for (int i = 0; hpyspec->defines[i] != NULL; i++) {
            HPyDef *src = hpyspec->defines[i];
            if (src->kind != HPyDef_Kind_Slot)
                continue;
            PyType_Slot *dst = &result[dst_idx++];
            dst->slot = hpy_slot_to_cpy_slot(src->slot.slot);
            dst->pfunc = src->slot.cpy_trampoline;
        }
    }

    // add the legacy slots (non-methods, non-members, non-getsets)
    if (hpyspec->legacy_slots != NULL) {
        PyType_Slot *legacy_slots = (PyType_Slot *)hpyspec->legacy_slots;
        for (int i = 0; legacy_slots[i].slot != 0; i++) {
            PyType_Slot *src = &legacy_slots[i];
            if (src->slot == Py_tp_methods || src->slot == Py_tp_members ||
                src->slot == Py_tp_getset)
                continue;
            PyType_Slot *dst = &result[dst_idx++];
            *dst = *src;
        }
    }

    // add the "real" methods
    PyMethodDef *pymethods = create_method_defs(hpyspec->defines, legacy_method_defs);
    if (pymethods == NULL) {
        PyMem_Free(result);
        return NULL;
    }
    result[dst_idx++] = (PyType_Slot){Py_tp_methods, pymethods};

    // add the "real" members
    PyMemberDef *pymembers = create_member_defs(hpyspec->defines, legacy_member_defs);
    if (pymembers == NULL) {
        PyMem_Free(pymethods);
        PyMem_Free(result);
        return NULL;
    }
    result[dst_idx++] = (PyType_Slot){Py_tp_members, pymembers};

    // add the "real" getsets
    PyGetSetDef *pygetsets = create_getset_defs(hpyspec->defines, legacy_getset_defs);
    if (pygetsets == NULL) {
        PyMem_Free(pymembers);
        PyMem_Free(pymethods);
        PyMem_Free(result);
        return NULL;
    }
    result[dst_idx++] = (PyType_Slot){Py_tp_getset, pygetsets};

    // add the NULL sentinel at the end
    result[dst_idx++] = (PyType_Slot){0, NULL};
    if (dst_idx != total_slot_count + 1)
        Py_FatalError("bogus slot count in create_slot_defs");
    return result;
}

static int check_unknown_params(HPyType_SpecParam *params, const char *name)
{
    if (params == NULL)
        return 0;

    int found_base = 0, found_basestuple = 0;
    for (HPyType_SpecParam *p = params; p->kind != 0; p++) {
        switch (p->kind) {
            case HPyType_SpecParam_Base:
                found_base++;
                break;
            case HPyType_SpecParam_BasesTuple:
                found_basestuple++;
                break;

            default:
                PyErr_Format(PyExc_TypeError,
                    "unknown HPyType_SpecParam specification for '%s'",
                    name);
                return -1;
        }
    }
    if (found_basestuple > 1) {
        PyErr_SetString(PyExc_TypeError,
            "multiple specifications of HPyType_SpecParam_BasesTuple");
        return -1;
    }
    if (found_base && found_basestuple) {
        PyErr_SetString(PyExc_TypeError,
            "cannot specify both HPyType_SpecParam_Base and "
            "HPytype_SpecParam_BasesTuple");
        return -1;
    }
    return 0;
}

static PyObject *build_bases_from_params(HPyType_SpecParam *params)
{
    if (params == NULL)
        return NULL;

    int found_base = 0;
    for (HPyType_SpecParam *p = params; p->kind != 0; p++) {
        switch (p->kind) {
            case HPyType_SpecParam_Base:
                /* count the base entries (multiple entries are fine) */
                found_base++;
                break;
            case HPyType_SpecParam_BasesTuple:
                /* if there is instead a complete base tuple, just return it */
                return _h2py(p->object);
        }
    }
    if (found_base == 0)
        return NULL;

    PyObject *tup = PyTuple_New(found_base);
    if (tup == NULL)
        return NULL;

    found_base = 0;
    for (HPyType_SpecParam *p = params; p->kind != 0; p++) {
        if (p->kind == HPyType_SpecParam_Base) {
            PyObject *base = _h2py(p->object);
            Py_INCREF(base);
            PyTuple_SET_ITEM(tup, found_base, base);
            found_base++;
        }
    }
    return tup;
}

_HPy_HIDDEN HPy
ctx_Type_FromSpec(HPyContext ctx, HPyType_Spec *hpyspec,
                  HPyType_SpecParam *params)
{
    if (check_unknown_params(params, hpyspec->name) < 0) {
        return HPy_NULL;
    }
    PyType_Spec *spec = PyMem_Calloc(1, sizeof(PyType_Spec));
    if (spec == NULL) {
        PyErr_NoMemory();
        return HPy_NULL;
    }
    spec->name = hpyspec->name;
    spec->basicsize = hpyspec->basicsize;
    spec->itemsize = hpyspec->itemsize;
    spec->flags = hpyspec->flags;
    spec->slots = create_slot_defs(hpyspec);
    if (spec->slots == NULL) {
        PyMem_Free(spec);
        return HPy_NULL;
    }
    PyObject *bases = build_bases_from_params(params);
    if (PyErr_Occurred()) {
        return HPy_NULL;
    }
    PyObject *result = PyType_FromSpecWithBases(spec, bases);
    /* note that we do NOT free the memory which was allocated by
       create_method_defs, because that one is referenced internally by
       CPython (which probably assumes it's statically allocated) */
    PyMem_Free(spec->slots);
    PyMem_Free(spec);
    return _py2h(result);
}

_HPy_HIDDEN HPy
ctx_New(HPyContext ctx, HPy h_type, void **data)
{
    PyObject *tp = _h2py(h_type);
    if (!PyType_Check(tp)) {
        PyErr_SetString(PyExc_TypeError, "HPy_New arg 1 must be a type");
        return HPy_NULL;
    }

    PyObject *result = PyObject_New(PyObject, (PyTypeObject*)tp);
    if (!result)
        return HPy_NULL;

    *data = (void*)result;
    return _py2h(result);
}

_HPy_HIDDEN HPy
ctx_Type_GenericNew(HPyContext ctx, HPy h_type, HPy *args, HPy_ssize_t nargs, HPy kw)
{
    PyTypeObject *type = (PyTypeObject *)_h2py(h_type);
    PyObject *res = type->tp_alloc(type, 0);
    return _py2h(res);
}
