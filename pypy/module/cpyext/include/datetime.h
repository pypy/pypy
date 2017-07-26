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
    PyTypeObject *TZInfoType;

    /* constructors */
    PyObject *(*Date_FromDate)(int, int, int, PyTypeObject*);
    PyObject *(*DateTime_FromDateAndTime)(int, int, int, int, int, int, int,
        PyObject*, PyTypeObject*);
    PyObject *(*Time_FromTime)(int, int, int, int, PyObject*, PyTypeObject*);
    PyObject *(*Delta_FromDelta)(int, int, int, int, PyTypeObject*);
} PyDateTime_CAPI;

PyAPI_DATA(PyDateTime_CAPI*) PyDateTimeAPI;
#define PyDateTime_IMPORT                           \
    do {                                            \
        if(PyDateTimeAPI==NULL)                     \
            PyDateTimeAPI = _PyDateTime_Import();   \
    } while (0)

typedef struct {
    PyObject_HEAD
} PyDateTime_Delta;

typedef struct {
    PyObject_HEAD
} PyDateTime_Date;

typedef struct {
    PyObject_HEAD
} PyDateTime_Time;

typedef struct {
    PyObject_HEAD
} PyDateTime_DateTime;

typedef struct {
    PyObject_HEAD
} PyDateTime_TZInfo;

/* Macros for accessing constructors in a simplified fashion. */
#define PyDate_FromDate(year, month, day) \
    PyDateTimeAPI->Date_FromDate(year, month, day, PyDateTimeAPI->DateType)

#define PyDateTime_FromDateAndTime(year, month, day, hour, min, sec, usec) \
    PyDateTimeAPI->DateTime_FromDateAndTime(year, month, day, hour, \
        min, sec, usec, Py_None, PyDateTimeAPI->DateTimeType)

#define PyTime_FromTime(hour, minute, second, usecond) \
    PyDateTimeAPI->Time_FromTime(hour, minute, second, usecond, \
        Py_None, PyDateTimeAPI->TimeType)

#define PyDelta_FromDSU(days, seconds, useconds) \
    PyDateTimeAPI->Delta_FromDelta(days, seconds, useconds, 1, \
        PyDateTimeAPI->DeltaType)

#ifdef __cplusplus
}
#endif
#endif
