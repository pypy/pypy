#ifndef DATETIME_H
#define DATETIME_H
#ifdef __cplusplus
extern "C" {
#endif

/* Define structure for C API. */
typedef struct {
    /* type objects */
    PyTypeObject *DateType;
    PyTypeObject *DateTimeType;
    PyTypeObject *TimeType;
    PyTypeObject *DeltaType;
} PyDateTime_CAPI;

#define PyDateTime_IMPORT _PyDateTime_Import()

typedef struct {
    PyObject_HEAD
} PyDateTime_Delta;

#ifdef __cplusplus
}
#endif
#endif
