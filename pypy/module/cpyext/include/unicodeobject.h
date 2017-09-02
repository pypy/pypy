#ifndef Py_UNICODEOBJECT_H
#define Py_UNICODEOBJECT_H

#ifdef __cplusplus
extern "C" {
#endif

#include "cpyext_unicodeobject.h"

#define PyUnicode_Check(op) \
		 PyType_FastSubclass((op)->ob_type, Py_TPFLAGS_UNICODE_SUBCLASS)
#define PyUnicode_CheckExact(op) ((op)->ob_type == &PyUnicode_Type)

#ifdef __cplusplus
}
#endif
#endif /* !Py_UNICODEOBJECT_H */
