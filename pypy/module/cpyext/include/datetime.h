#ifndef DATETIME_H
#define DATETIME_H
#ifdef __cplusplus
extern "C" {
#endif


#define PyDateTime_GET_YEAR(o)  _PyDateTime_GET_YEAR((PyDateTime_Date*)(o))
#define PyDateTime_GET_MONTH(o) _PyDateTime_GET_MONTH((PyDateTime_Date*)(o))
#define PyDateTime_GET_DAY(o)   _PyDateTime_GET_DAY((PyDateTime_Date*)(o))

#define PyDateTime_DATE_GET_HOUR(o)        _PyDateTime_DATE_GET_HOUR((PyDateTime_DateTime*)(o))
#define PyDateTime_DATE_GET_MINUTE(o)      _PyDateTime_DATE_GET_MINUTE((PyDateTime_DateTime*)(o))
#define PyDateTime_DATE_GET_SECOND(o)      _PyDateTime_DATE_GET_SECOND((PyDateTime_DateTime*)(o))
#define PyDateTime_DATE_GET_MICROSECOND(o) _PyDateTime_DATE_GET_MICROSECOND((PyDateTime_DateTime*)(o))

#define PyDateTime_TIME_GET_HOUR(o)        _PyDateTime_TIME_GET_HOUR((PyDateTime_Time*)(o))
#define PyDateTime_TIME_GET_MINUTE(o)      _PyDateTime_TIME_GET_MINUTE((PyDateTime_Time*)(o))
#define PyDateTime_TIME_GET_SECOND(o)      _PyDateTime_TIME_GET_SECOND((PyDateTime_Time*)(o))
#define PyDateTime_TIME_GET_MICROSECOND(o) _PyDateTime_TIME_GET_MICROSECOND((PyDateTime_Time*)(o))

#define PyDateTime_DELTA_GET_DAYS(o)         _PyDateTime_DELTA_GET_DAYS((PyDateTime_Delta*)(o))
#define PyDateTime_DELTA_GET_SECONDS(o)      _PyDateTime_DELTA_GET_SECONDS((PyDateTime_Delta*)(o))
#define PyDateTime_DELTA_GET_MICROSECONDS(o) _PyDateTime_DELTA_GET_MICROSECONDS((PyDateTime_Delta*)(o))



/* Define structure for C API. */
typedef struct {
    /* type objects */
    PyTypeObject *DateType;
    PyTypeObject *DateTimeType;
    PyTypeObject *TimeType;
    PyTypeObject *DeltaType;
    PyTypeObject *TZInfoType;
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

#ifdef __cplusplus
}
#endif
#endif
