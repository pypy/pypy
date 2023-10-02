/*
 * Helper functions to create struct sequences.
 *
 * These are not part of the HPy context or ABI, but instead are just helpers
 * that delegate to the relevant HPy/CPython APIs.
 */

#include "hpy.h"

#include <string.h> // for strncpy/strncpy_s
#include <stdio.h>

const char * const HPyStructSequence_UnnamedField = "_";

HPyAPI_HELPER HPy
HPyStructSequence_NewType(HPyContext *ctx, HPyStructSequence_Desc *desc)
{
    HPy_ssize_t i;

    if (desc->name == NULL) {
        HPyErr_SetString(ctx, ctx->h_SystemError,
                "Struct sequence descriptor does not define the name field.");
        return HPy_NULL;
    }

    for (i = 0; desc->fields[i].name != NULL; i++) {
    }

#ifndef HPY_ABI_CPYTHON
    HPyTracker ht;
    HPy fields, args, kwds, defs, docstring, n_fields, h_field, h_modname;
    HPy result = HPy_NULL;
    const char *name, *s;
    char *modname;

    HPy collections = HPyImport_ImportModule(ctx, "collections");
    if (HPy_IsNull(collections)) {
        return HPy_NULL;
    }
    HPy namedtuple = HPy_GetAttr_s(ctx, collections, "namedtuple");
    HPy_Close(ctx, collections);
    if (HPy_IsNull(namedtuple)) {
        return HPy_NULL;
    }
    ht = HPyTracker_New(ctx, 9);
    HPyTracker_Add(ctx, ht, namedtuple);


    HPyTupleBuilder argsBuilder = HPyTupleBuilder_New(ctx, 2);
    HPyTupleBuilder fieldsBuilder = HPyTupleBuilder_New(ctx, i);
    HPyTupleBuilder defsBuilder = HPyTupleBuilder_New(ctx, i);

    HPy h_name = HPyUnicode_FromString(ctx, "tmpname");
    if (HPy_IsNull(h_name)) {
        goto error;
    }
    HPyTupleBuilder_Set(ctx, argsBuilder, 0, h_name);
    HPy_Close(ctx, h_name);

    i = 0;
    for (name = desc->fields[i].name; name != NULL; name = desc->fields[++i].name) {
        h_field = HPyUnicode_FromString(ctx, name);
        if (HPy_IsNull(h_field)) {
            HPyTupleBuilder_Cancel(ctx, argsBuilder);
            HPyTupleBuilder_Cancel(ctx, fieldsBuilder);
            HPyTupleBuilder_Cancel(ctx, defsBuilder);
            goto error;
        }
        HPyTupleBuilder_Set(ctx, fieldsBuilder, i, h_field);
        HPyTupleBuilder_Set(ctx, defsBuilder, i, ctx->h_None);
        HPy_Close(ctx, h_field);
    }
    fields = HPyTupleBuilder_Build(ctx, fieldsBuilder);
    if (HPy_IsNull(fields)) {
        HPyTupleBuilder_Cancel(ctx, argsBuilder);
        HPyTupleBuilder_Cancel(ctx, defsBuilder);
        goto error;
    }
    HPyTracker_Add(ctx, ht, fields);

    defs = HPyTupleBuilder_Build(ctx, defsBuilder);
    if (HPy_IsNull(defs)) {
        HPyTupleBuilder_Cancel(ctx, argsBuilder);
        goto error;
    }
    HPyTracker_Add(ctx, ht, defs);

    HPyTupleBuilder_Set(ctx, argsBuilder, 1, fields);
    args = HPyTupleBuilder_Build(ctx, argsBuilder);
    if (HPy_IsNull(args)) {
        goto error;
    }
    HPyTracker_Add(ctx, ht, args);

    kwds = HPyDict_New(ctx);
    if (HPy_IsNull(kwds)) {
        goto error;
    }
    HPyTracker_Add(ctx, ht, kwds);
    if (HPy_SetItem_s(ctx, kwds, "rename", ctx->h_True) < 0) {
        goto error;
    }
    if (HPy_SetItem_s(ctx, kwds, "defaults", defs) < 0) {
        goto error;
    }

    result = HPy_CallTupleDict(ctx, namedtuple, args, kwds);
    if (HPy_IsNull(result)) {
        goto error;
    }

    if (desc->doc) {
        docstring = HPyUnicode_FromString(ctx, desc->doc);
        if (HPy_IsNull(docstring)) {
            goto error;
        }
        HPyTracker_Add(ctx, ht, docstring);
    } else {
        docstring = ctx->h_None;
    }
    if (HPy_SetAttr_s(ctx, result, "__doc__", docstring) < 0) {
        goto error;
    }

    n_fields = HPyLong_FromSsize_t(ctx, i);
    if (HPy_IsNull(n_fields)) {
        goto error;
    }
    HPyTracker_Add(ctx, ht, n_fields);
    if (HPy_SetAttr_s(ctx, result, "n_fields", n_fields) < 0) {
        goto error;
    }

    /* Set the type name and qualname */
    s = strrchr(desc->name, '.');
    if (s == NULL) {
        s = desc->name;
        modname = NULL;
    }
    else {
        /* TODO: Replace this by using 'HPyUnicode_FromStringAndSize' or similar
           once available. */
        const size_t n_modname = s - desc->name;
        modname = (char *)malloc((n_modname + 1) * sizeof(char));
#ifdef _WIN32
        strncpy_s(modname, n_modname + 1, desc->name, n_modname);
#else
        strncpy(modname, desc->name, n_modname);
#endif
        modname[n_modname] = '\0';

        // now, advance by one to skip '.'
        s++;
    }

    h_name = HPyUnicode_FromString(ctx, s);
    if (HPy_IsNull(h_name)) {
        goto error;
    }
    HPyTracker_Add(ctx, ht, h_name);
    if (HPy_SetAttr_s(ctx, result, "__name__", h_name) < 0 ||
            HPy_SetAttr_s(ctx, result, "__qualname__", h_name) < 0) {
        goto error;
    }

    if (modname != NULL) {
        h_modname = HPyUnicode_FromString(ctx, modname);
        free(modname);
        if (HPy_IsNull(h_modname)) {
            goto error;
        }
        HPyTracker_Add(ctx, ht, h_modname);
        if (HPy_SetAttr_s(ctx, result, "__module__", h_modname) < 0) {
            goto error;
        }
    }

    HPyTracker_Close(ctx, ht);
    return result;

 error:
    HPyTracker_Close(ctx, ht);
    HPy_Close(ctx, result);
    return HPy_NULL;
#else
    PyStructSequence_Desc d = {
        .name = desc->name,
#if PY_VERSION_HEX < 0x03090000
        // In Python 3.8.x or earlier, the docstring MUST NOT be NULL
        .doc = (desc->doc != NULL ? desc->doc : ""),
#else
        .doc = desc->doc,
#endif
        .fields = (PyStructSequence_Field *)desc->fields,
        .n_in_sequence = (int)i
    };
    return _py2h((PyObject*) PyStructSequence_NewType(&d));
#endif
}

HPyAPI_HELPER HPy
HPyStructSequence_New(HPyContext *ctx, HPy type, HPy_ssize_t nargs, HPy *args)
{
    static const char *s_n_fields = "n_fields";
#ifndef HPY_ABI_CPYTHON
    if (!HPy_HasAttr_s(ctx, type, s_n_fields)) {
        HPyErr_Clear(ctx);
        HPyErr_Format(ctx, ctx->h_TypeError,
                "object '%R' does not look like a struct sequence type ", type);
        return HPy_NULL;
    }
    HPy tuple = HPyTuple_FromArray(ctx, args, nargs);
    if (HPy_IsNull(tuple)) {
        return HPy_NULL;
    }
    HPy result = HPy_CallTupleDict(ctx, type, tuple, HPy_NULL);
    HPy_Close(ctx, tuple);
    return result;
#else
    PyTypeObject *tp;
    PyObject *name, *v, *seq, *item;
    Py_ssize_t n_fields, i;

    tp = (PyTypeObject *)_h2py(type);
    name = PyUnicode_FromStringAndSize(s_n_fields, sizeof(s_n_fields));
    // CPython also accesses the dict directly
#if PY_VERSION_HEX >= 0x030C0000
    PyObject *dict = PyType_GetDict(tp);
#else
    PyObject *dict = tp->tp_dict;
#endif
    v = PyDict_GetItemWithError(dict, name);
#if PY_VERSION_HEX >= 0x030C0000
    Py_DECREF(dict);
#endif
    Py_DECREF(name);
    if (v == NULL && !PyErr_Occurred()) {
        goto type_error;
    }
    n_fields = PyLong_AsSsize_t(v);
    seq = PyStructSequence_New(tp);
    if (seq == NULL) {
        goto type_error;
    }
    if (n_fields != nargs) {
        PyErr_Format(PyExc_TypeError,
                     "expected exactly %d arguments but got %d",
                     n_fields, nargs);
        Py_DECREF(seq);
        goto error;
    }

    for (i = 0; i < nargs; i++) {
        item = _h2py(args[i]);
        Py_INCREF(item);
        PyStructSequence_SetItem(seq, i, item);
    }
    return _py2h(seq);

type_error:
    /* The error behavior seems not to be consistent. If anything goes
       wrong, we will convert it to a TypeError here. */
    PyErr_Clear();
    PyErr_Format(PyExc_TypeError,
                 "type '%s' does not look like a struct sequence type",
                 tp->tp_name);

error:
    return HPy_NULL;
#endif
}
