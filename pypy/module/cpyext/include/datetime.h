#ifndef DATETIME_H
#define DATETIME_H
#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_datetime.h"

/* # of bytes for year, month, and day. */
#define _PyDateTime_DATE_DATASIZE 4

/* # of bytes for hour, minute, second, and usecond. */
#define _PyDateTime_TIME_DATASIZE 6

/* # of bytes for year, month, day, hour, minute, second, and usecond. */
#define _PyDateTime_DATETIME_DATASIZE 10

/* "magic" constant used to partially protect against developer mistakes. */
#define DATETIME_API_MAGIC 0x414548d5

PyAPI_DATA(PyDateTime_CAPI*) PyDateTimeAPI;

#define PyDateTime_IMPORT (PyDateTimeAPI = _PyDateTime_Import())

/* Macros for accessing constructors in a simplified fashion. */
#define PyDate_FromDate(year, month, day) \
    PyDateTimeAPI->Date_FromDate(year, month, day, PyDateTimeAPI->DateType)

#define PyDateTime_FromDateAndTime(year, month, day, hour, min, sec, usec) \
    PyDateTimeAPI->DateTime_FromDateAndTime(year, month, day, hour, \
        min, sec, usec, Py_None, PyDateTimeAPI->DateTimeType)

#define PyDateTime_FromDateAndTimeAndFold(year, month, day, hour, min, sec, usec, fold) \
    PyDateTimeAPI->DateTime_FromDateAndTimeAndFold(year, month, day, hour, \
        min, sec, usec, Py_None, fold, PyDateTimeAPI->DateTimeType)

#define PyTime_FromTime(hour, minute, second, usecond) \
    PyDateTimeAPI->Time_FromTime(hour, minute, second, usecond, \
        Py_None, PyDateTimeAPI->TimeType)

#define PyTime_FromTimeAndFold(hour, minute, second, usecond, fold) \
    PyDateTimeAPI->Time_FromTimeAndFold(hour, minute, second, usecond, \
        Py_None, fold, PyDateTimeAPI->TimeType)

#define PyDelta_FromDSU(days, seconds, useconds) \
    PyDateTimeAPI->Delta_FromDelta(days, seconds, useconds, 1, \
        PyDateTimeAPI->DeltaType)

#ifdef Py_BUILD_CORE

/* Macros for type checking when building the Python core. */
#define PyDate_Check(op) PyObject_TypeCheck(op, &PyDateTime_DateType)
#define PyDate_CheckExact(op) (Py_TYPE(op) == &PyDateTime_DateType)

#define PyDateTime_Check(op) PyObject_TypeCheck(op, &PyDateTime_DateTimeType)
#define PyDateTime_CheckExact(op) (Py_TYPE(op) == &PyDateTime_DateTimeType)

#define PyTime_Check(op) PyObject_TypeCheck(op, &PyDateTime_TimeType)
#define PyTime_CheckExact(op) (Py_TYPE(op) == &PyDateTime_TimeType)

#define PyDelta_Check(op) PyObject_TypeCheck(op, &PyDateTime_DeltaType)
#define PyDelta_CheckExact(op) (Py_TYPE(op) == &PyDateTime_DeltaType)

#define PyTZInfo_Check(op) PyObject_TypeCheck(op, &PyDateTime_TZInfoType)
#define PyTZInfo_CheckExact(op) (Py_TYPE(op) == &PyDateTime_TZInfoType)

#else

#endif  /* Py_BUILD_CORE */


#ifdef __cplusplus
}
#endif
#endif
