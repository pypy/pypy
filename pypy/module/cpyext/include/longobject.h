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

#ifdef __cplusplus
}
#endif
#endif /* !Py_LONGOBJECT_H */
