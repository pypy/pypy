#include "Python.h"

PyObject *
PyType_FromSpec(PyType_Spec *spec)
{
    return PyType_FromSpecWithBases(spec, NULL);
}
/* 
 * Mangle to _PyPy_subtype_dealloc for translation.
 * For tests, we want to mangle as if it were a c-api function so
 * it will not be confused with the host's similarly named function
 */

#ifdef CPYEXT_TESTS
#define _Py_subtype_dealloc _cpyexttest_subtype_dealloc
#define PyType_IsSubtype cpyexttestType_IsSubtype
#ifdef __GNUC__
__attribute__((visibility("default")))
#else
__declspec(dllexport)
#endif
#else  /* CPYEXT_TESTS */
#define _Py_subtype_dealloc _PyPy_subtype_dealloc
#define PyType_IsSubtype PyPyType_IsSubtype
#endif  /* CPYEXT_TESTS */
void
_Py_subtype_dealloc(PyObject *obj)
{
    PyTypeObject *pto = obj->ob_type;
    PyTypeObject *base = pto;
    /* This wrapper is created on a specific type, call it w_A.
       We wish to call the dealloc function from one of the base classes of w_A,
       the first of which is not this function itself.
       w_obj is an instance of w_A or one of its subclasses. So climb up the
       inheritance chain until base.c_tp_dealloc is exactly this_func, and then
       continue on up until they differ.
       */
    while (base->tp_dealloc != &_Py_subtype_dealloc)
    {
        base = base->tp_base;
        assert(base);
    }
    while (base->tp_dealloc == &_Py_subtype_dealloc)
    {
        base = base->tp_base;
        assert(base);
    }
    /* XXX call tp_del if necessary */
    base->tp_dealloc(obj);
    /* XXX cpy decrefs the pto here but we do it in the base-dealloc
       hopefully this does not clash with the memory model assumed in
       extension modules */
}

unsigned long
PyType_GetFlags(PyTypeObject *type)
{
    return type->tp_flags;
}

PyObject *
PyType_GenericNew(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    return type->tp_alloc(type, 0);
}


/* type test with subclassing support */

static int
type_is_subtype_base_chain(PyTypeObject *a, PyTypeObject *b)
{
    do {
        if (a == b)
            return 1;
        a = a->tp_base;
    } while (a != NULL);

    return (b == &PyBaseObject_Type);
}

int
PyType_IsSubtype(PyTypeObject *a, PyTypeObject *b)
{
    PyObject *mro;

    mro = a->tp_mro;
    if (mro != NULL) {
        /* Deal with multiple inheritance without recursion
           by walking the MRO tuple */
        Py_ssize_t i, n;
        assert(PyTuple_Check(mro));
        n = PyTuple_GET_SIZE(mro);
        for (i = 0; i < n; i++) {
            if (PyTuple_GET_ITEM(mro, i) == (PyObject *)b)
                return 1;
        }
        return 0;
    }
    else
        /* a is not completely initialized yet; follow tp_base */
        return type_is_subtype_base_chain(a, b);
}

/* Get the module of the first superclass where the module has the
 * given PyModuleDef.
 * Implemented by walking the MRO, is relatively slow.
 *
 * This is internal API for experimentation within stdlib. Discussion:
 * https://mail.python.org/archives/list/capi-sig@python.org/thread/T3P2QNLNLBRFHWSKYSTPMVEIL2EEKFJU/
 */
PyObject *
_PyType_GetModuleByDef(PyTypeObject *type, struct PyModuleDef *def)
{
    assert(PyType_Check(type));
    PyObject *mro = type->tp_mro;
    // The type must be ready
    assert(mro != NULL);
    assert(PyTuple_Check(mro));
    // mro_invoke() ensures that the type MRO cannot be empty, so we don't have
    // to check i < PyTuple_GET_SIZE(mro) at the first loop iteration.
    assert(PyTuple_GET_SIZE(mro) >= 1);
    Py_ssize_t n = PyTuple_GET_SIZE(mro);
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *super = PyTuple_GET_ITEM(mro, i);
        // _PyType_GetModuleByDef() must only be called on a heap type created
        // by PyType_FromModuleAndSpec() or on its subclasses.
        // type_ready_mro() ensures that a static type cannot inherit from a
        // heap type.
        assert(PyType_HasFeature(type, Py_TPFLAGS_HEAPTYPE));
        if(!PyType_HasFeature((PyTypeObject *)super, Py_TPFLAGS_HEAPTYPE)) {
            // Static types in the MRO need to be skipped
            continue;
        }

        PyHeapTypeObject *ht = (PyHeapTypeObject*)super;
        PyObject *module = ht->ht_module;
        if (module && PyModule_GetDef(module) == def) {
            return module;
        }
    }
    PyErr_Format(
        PyExc_TypeError,
        "_PyType_GetModuleByDef: No superclass of '%s' has the given module",
        type->tp_name);
    return NULL;
}
