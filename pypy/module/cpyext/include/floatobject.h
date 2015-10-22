
/* Float object interface */

#ifndef Py_FLOATOBJECT_H
#define Py_FLOATOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

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

#ifdef __cplusplus
}
#endif
#endif /* !Py_FLOATOBJECT_H */
