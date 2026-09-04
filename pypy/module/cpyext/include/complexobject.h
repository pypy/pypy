/* Complex object interface */

#ifndef Py_COMPLEXOBJECT_H
#define Py_COMPLEXOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

typedef struct Py_complex_t {
    double real;
    double imag;
} Py_complex;

typedef struct {
    PyObject_HEAD
    Py_complex cval;
} PyComplexObject;

PyAPI_FUNC(Py_complex) PyComplex_AsCComplex(PyObject *obj);
PyAPI_FUNC(PyObject *) PyComplex_FromCComplex(Py_complex c);

PyAPI_FUNC(Py_complex) _Py_c_sum(Py_complex, Py_complex);
PyAPI_FUNC(Py_complex) _Py_c_diff(Py_complex, Py_complex);
PyAPI_FUNC(Py_complex) _Py_c_neg(Py_complex);
PyAPI_FUNC(Py_complex) _Py_c_prod(Py_complex, Py_complex);
PyAPI_FUNC(Py_complex) _Py_c_quot(Py_complex, Py_complex);
PyAPI_FUNC(Py_complex) _Py_c_pow(Py_complex, Py_complex);
PyAPI_FUNC(double) _Py_c_abs(Py_complex);

#ifdef __cplusplus
}
#endif
#endif /* !Py_COMPLEXOBJECT_H */
