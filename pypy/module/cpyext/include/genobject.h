#ifndef Py_GENOBJECT_H
#define Py_GENOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#ifndef Py_LIMITED_API
#include "cpyext_genobject.h"

PyAPI_FUNC(PyCodeObject *) PyGen_GetCode(PyGenObject *gen);
#endif /* !Py_LIMITED_API */

#ifdef __cplusplus
}
#endif
#endif /* !Py_GENOBJECT_H */
