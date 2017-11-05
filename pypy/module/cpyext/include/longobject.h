#ifndef Py_LONGOBJECT_H
#define Py_LONGOBJECT_H

#include <stdlib.h>

#ifdef __cplusplus
extern "C" {
#endif

/* why does cpython redefine these, and even supply an implementation in mystrtoul.c?
PyAPI_FUNC(unsigned long) PyOS_strtoul(const char *, char **, int);
PyAPI_FUNC(long) PyOS_strtol(const char *, char **, int);
*/

#define PyOS_strtoul strtoul
#define PyOS_strtol strtoul
#define PyLong_Check(op) \
		 PyType_FastSubclass((op)->ob_type, Py_TPFLAGS_LONG_SUBCLASS)
#define PyLong_CheckExact(op) ((op)->ob_type == &PyLong_Type)

#ifdef __cplusplus
}
#endif
#endif /* !Py_LONGOBJECT_H */
