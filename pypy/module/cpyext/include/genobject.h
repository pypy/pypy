#ifndef Py_GENOBJECT_H
#define Py_GENOBJECT_H
#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_genobject.h"

PyAPI_FUNC(PyCodeObject *) PyGen_GetCode(PyGenObject *gen);

#ifdef __cplusplus
}
#endif
#endif /* !Py_GENOBJECT_H */
