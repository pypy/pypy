
#include "Python.h"

Py_complex
PyComplex_AsCComplex(PyObject *obj)
{
    Py_complex result;
    _PyComplex_AsCComplex(obj, &result);
    return result;
}

PyObject *
PyComplex_FromCComplex(Py_complex c)
{
    return _PyComplex_FromCComplex(&c);
}

int
PyIndex_Check(PyObject *obj)
{
    /* Taken from cpython/Include/internal/pycore_abstract.h */
    if (obj == NULL)
        return 0;
    PyNumberMethods *tp_as_number = Py_TYPE(obj)->tp_as_number;
    return (tp_as_number != NULL && tp_as_number->nb_index != NULL);
}

int
PyNumber_Check(PyObject *obj)
{
    if (obj == NULL)
        return 0;
    PyNumberMethods *nb = Py_TYPE(obj)->tp_as_number;
    return nb && (nb->nb_index || nb->nb_int || nb->nb_float || PyComplex_Check(obj));
}


