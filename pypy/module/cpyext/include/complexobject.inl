/* Complex object inline functions */

#ifndef Py_COMPLEXOBJECT_INL
#define Py_COMPLEXOBJECT_INL
#ifdef __cplusplus
extern "C" {
#endif

Py_LOCAL_INLINE(Py_complex) PyComplex_AsCComplex(PyObject *obj)
{
    Py_complex result;
    _PyComplex_AsCComplex(obj, &result);
    return result;
}


#ifdef __cplusplus
}
#endif
#endif /* !Py_COMPLEXOBJECT_INL */
