
/* Tuple object implementation, stolen&adapted from CPython */

#include "Python.h"

/* Speed optimization to avoid frequent malloc/free of small tuples */
#ifndef PyTuple_MAXSAVESIZE
#define PyTuple_MAXSAVESIZE     20  /* Largest tuple to save on free list */
#endif
#ifndef PyTuple_MAXFREELIST
#define PyTuple_MAXFREELIST  2000  /* Maximum number of tuples of each size to save */
#endif

#if PyTuple_MAXSAVESIZE > 0
/* Entries 1 up to PyTuple_MAXSAVESIZE are free lists, entry 0 is the empty
   tuple () of which at most one instance will be allocated.
*/
static PyTupleObject *free_list[PyTuple_MAXSAVESIZE];
static int numfree[PyTuple_MAXSAVESIZE];
#endif

PyObject *
PyTuple_New(register Py_ssize_t size)
{
    register PyTupleObject *op;
    Py_ssize_t i;
    if (size < 0) {
        PyErr_BadInternalCall();
        return NULL;
    }
#if PyTuple_MAXSAVESIZE > 0
    if (size == 0 && free_list[0]) {
        op = free_list[0];
        Py_INCREF(op);
        return (PyObject *) op;
    }
    if (size < PyTuple_MAXSAVESIZE && (op = free_list[size]) != NULL) {
        free_list[size] = (PyTupleObject *) op->ob_item[0];
        numfree[size]--;
        _Py_NewReference((PyObject *)op);
    }
    else
#endif
    {
        Py_ssize_t nbytes = size * sizeof(PyObject *);
        /* Check for overflow */
        if (nbytes / sizeof(PyObject *) != (size_t)size ||
            (nbytes > PY_SSIZE_T_MAX - sizeof(PyTupleObject) - sizeof(PyObject *)))
        {
            return PyErr_NoMemory();
        }

        op = PyObject_GC_NewVar(PyTupleObject, &PyTuple_Type, size);
        if (op == NULL)
            return NULL;
    }
    for (i=0; i < size; i++)
        op->ob_item[i] = NULL;
#if PyTuple_MAXSAVESIZE > 0
    if (size == 0) {
        free_list[0] = op;
        ++numfree[0];
        Py_INCREF(op);          /* extra INCREF so that this is never freed */
    }
#endif
    _PyObject_GC_TRACK(op);
    return (PyObject *) op;
}

/* this is CPython's tupledealloc */
void
_PyPy_tuple_dealloc(register PyObject *_op)
{
    register PyTupleObject *op = (PyTupleObject *)_op;
    register Py_ssize_t i;
    register Py_ssize_t len =  Py_SIZE(op);
    PyObject_GC_UnTrack(op);
    Py_TRASHCAN_SAFE_BEGIN(op)
    if (len > 0) {
        i = len;
        while (--i >= 0)
            Py_XDECREF(op->ob_item[i]);
#if PyTuple_MAXSAVESIZE > 0
        if (len < PyTuple_MAXSAVESIZE &&
            numfree[len] < PyTuple_MAXFREELIST &&
            Py_TYPE(op) == &PyTuple_Type)
        {
            op->ob_item[0] = (PyObject *) free_list[len];
            numfree[len]++;
            free_list[len] = op;
            goto done; /* return */
        }
#endif
    }
    Py_TYPE(op)->tp_free((PyObject *)op);
done:
    Py_TRASHCAN_SAFE_END(op)
}
