
/* Float object interface */

#ifndef Py_FLOATOBJECT_H
#define Py_FLOATOBJECT_H

#ifdef _MSC_VER
#include <math.h>
#include <float.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    PyObject_HEAD
    double ob_fval;
} PyFloatObject;

#define PyFloat_STR_PRECISION 12

#ifdef Py_NAN
#define Py_RETURN_NAN return PyFloat_FromDouble(Py_NAN)
#endif

#define Py_RETURN_INF(sign) do                                  \
        if (copysign(1., sign) == 1.) {                         \
                return PyFloat_FromDouble(Py_HUGE_VAL); \
        } else {                                                \
                return PyFloat_FromDouble(-Py_HUGE_VAL);        \
        } while(0)

PyAPI_FUNC(int) PyFloat_Pack2(double x, char *p, int le);
PyAPI_FUNC(int) PyFloat_Pack4(double x, char *p, int le);
PyAPI_FUNC(int) PyFloat_Pack8(double x, char *p, int le);

PyAPI_FUNC(double) PyFloat_Unpack2(const char *p, int le);
PyAPI_FUNC(double) PyFloat_Unpack4(const char *p, int le);
PyAPI_FUNC(double) PyFloat_Unpack8(const char *p, int le);
PyAPI_FUNC(void) _PyFloat_InitState(void);

#ifdef __cplusplus
}
#endif
#endif /* !Py_FLOATOBJECT_H */
