/* Complex object interface */

#ifndef Py_COMPLEXOBJECT_H
#define Py_COMPLEXOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

/* fake PyComplexObject so that code that doesn't do direct field access works */
#define PyComplexObject PyObject

typedef struct Py_complex_t {
    double real;
    double imag;
} Py_complex;

/* generated function */
PyAPI_FUNC(void) _PyComplex_AsCComplex(PyObject *, Py_complex *);

Py_LOCAL_INLINE(Py_complex) PyComplex_AsCComplex(PyObject *obj)
{
    Py_complex result;
    _PyComplex_AsCComplex(obj, &result);
    return result;
}

#define PyComplex_FromCComplex(c) _PyComplex_FromCComplex(&c)

#ifdef __cplusplus
}
#endif
#endif /* !Py_COMPLEXOBJECT_H */
