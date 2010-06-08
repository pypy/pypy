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

#ifdef __cplusplus
}
#endif
#endif /* !Py_COMPLEXOBJECT_H */
